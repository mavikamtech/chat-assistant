"""AWS RDS client for financial data queries."""

import logging
from typing import Any, Dict, List, Optional, Tuple
import asyncio
from contextlib import asynccontextmanager

import aioboto3
import asyncpg
from botocore.exceptions import ClientError, NoCredentialsError

from mavik_common.errors import (
    RDSError,
    AWSServiceError,
)

logger = logging.getLogger(__name__)


class RDSClient:
    """AWS RDS client with connection pooling and retry logic."""

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        db_cluster_endpoint: Optional[str] = None,
        db_name: str = "mavik_findb",
        db_user: Optional[str] = None,
        use_iam_auth: bool = True,
        min_pool_size: int = 5,
        max_pool_size: int = 20,
    ):
        """Initialize RDS client.

        Args:
            region_name: AWS region
            aws_access_key_id: Optional explicit AWS credentials
            aws_secret_access_key: Optional explicit AWS credentials
            db_cluster_endpoint: RDS cluster endpoint
            db_name: Database name
            db_user: Database user (if not using IAM auth)
            use_iam_auth: Whether to use IAM database authentication
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.region_name = region_name
        self.db_cluster_endpoint = db_cluster_endpoint
        self.db_name = db_name
        self.db_user = db_user
        self.use_iam_auth = use_iam_auth
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool = None

        try:
            session_kwargs = {"region_name": region_name}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs.update({
                    "aws_access_key_id": aws_access_key_id,
                    "aws_secret_access_key": aws_secret_access_key,
                })

            self.session = aioboto3.Session(**session_kwargs)

        except Exception as e:
            raise AWSServiceError(f"Failed to initialize RDS client: {e}")

    async def initialize_pool(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            return

        try:
            if self.use_iam_auth and self.db_cluster_endpoint:
                # Generate IAM auth token
                async with self.session.client("rds") as rds_client:
                    auth_token = rds_client.generate_db_auth_token(
                        DBHostname=self.db_cluster_endpoint.split(":")[0],
                        Port=5432,
                        DBUsername=self.db_user or "mavik_readonly",
                    )

                connection_params = {
                    "host": self.db_cluster_endpoint.split(":")[0],
                    "port": 5432,
                    "database": self.db_name,
                    "user": self.db_user or "mavik_readonly",
                    "password": auth_token,
                    "ssl": "require",
                }
            else:
                # Use environment variables for credentials in non-IAM mode
                connection_params = {
                    "host": self.db_cluster_endpoint.split(":")[0] if self.db_cluster_endpoint else "localhost",
                    "port": 5432,
                    "database": self.db_name,
                    "user": self.db_user,
                    # Password should be set via environment variables
                }

            self._pool = await asyncpg.create_pool(
                **connection_params,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=60,
            )

            logger.info(f"RDS connection pool initialized with {self.min_pool_size}-{self.max_pool_size} connections")

        except Exception as e:
            raise RDSError(f"Failed to initialize connection pool: {e}")

    async def close_pool(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("RDS connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if self._pool is None:
            await self.initialize_pool()

        try:
            async with self._pool.acquire() as connection:
                yield connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise RDSError(f"Connection error: {e}")

    async def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_all: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Optional query parameters
            fetch_all: Whether to fetch all results or just one

        Returns:
            List of result dictionaries

        Raises:
            RDSError: For database errors
        """
        try:
            async with self.get_connection() as conn:
                logger.debug(f"Executing query: {query}")

                if fetch_all:
                    rows = await conn.fetch(query, *(params or ()))
                else:
                    row = await conn.fetchrow(query, *(params or ()))
                    rows = [row] if row else []

                # Convert asyncpg.Record to dict
                results = [dict(row) for row in rows]

                logger.debug(f"Query returned {len(results)} rows")
                return results

        except asyncpg.PostgresError as e:
            raise RDSError(f"PostgreSQL error: {e}")
        except Exception as e:
            raise RDSError(f"Query execution error: {e}")

    async def execute_command(
        self,
        command: str,
        params: Optional[Tuple] = None,
    ) -> str:
        """Execute a non-SELECT command (INSERT, UPDATE, DELETE).

        Args:
            command: SQL command string
            params: Optional command parameters

        Returns:
            Command status string

        Raises:
            RDSError: For database errors
        """
        try:
            async with self.get_connection() as conn:
                logger.debug(f"Executing command: {command}")

                status = await conn.execute(command, *(params or ()))

                logger.debug(f"Command executed: {status}")
                return status

        except asyncpg.PostgresError as e:
            raise RDSError(f"PostgreSQL error: {e}")
        except Exception as e:
            raise RDSError(f"Command execution error: {e}")

    async def get_property_metrics(
        self,
        asset_type: Optional[str] = None,
        geographic_region: Optional[str] = None,
        min_square_footage: Optional[float] = None,
        max_square_footage: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query property metrics with filters.

        Args:
            asset_type: Optional asset type filter
            geographic_region: Optional region filter
            min_square_footage: Minimum square footage
            max_square_footage: Maximum square footage
            limit: Maximum number of results

        Returns:
            List of property metrics
        """
        try:
            conditions = []
            params = []
            param_count = 0

            if asset_type:
                param_count += 1
                conditions.append(f"asset_type = ${param_count}")
                params.append(asset_type)

            if geographic_region:
                param_count += 1
                conditions.append(f"geographic_region = ${param_count}")
                params.append(geographic_region)

            if min_square_footage is not None:
                param_count += 1
                conditions.append(f"rentable_square_footage >= ${param_count}")
                params.append(min_square_footage)

            if max_square_footage is not None:
                param_count += 1
                conditions.append(f"rentable_square_footage <= ${param_count}")
                params.append(max_square_footage)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            param_count += 1

            query = f"""
                SELECT
                    property_id,
                    asset_type,
                    geographic_region,
                    rentable_square_footage,
                    cap_rate,
                    occupancy_rate,
                    rent_per_sqft,
                    noi_per_sqft,
                    construction_year,
                    last_updated
                FROM property_metrics
                WHERE {where_clause}
                ORDER BY last_updated DESC
                LIMIT ${param_count}
            """
            params.append(limit)

            return await self.execute_query(query, tuple(params))

        except Exception as e:
            raise RDSError(f"Error querying property metrics: {e}")

    async def get_tenant_information(
        self,
        property_id: Optional[str] = None,
        tenant_name: Optional[str] = None,
        min_lease_value: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query tenant information with filters.

        Args:
            property_id: Optional property ID filter
            tenant_name: Optional tenant name filter (partial match)
            min_lease_value: Minimum lease value
            limit: Maximum number of results

        Returns:
            List of tenant information
        """
        try:
            conditions = []
            params = []
            param_count = 0

            if property_id:
                param_count += 1
                conditions.append(f"property_id = ${param_count}")
                params.append(property_id)

            if tenant_name:
                param_count += 1
                conditions.append(f"tenant_name ILIKE ${param_count}")
                params.append(f"%{tenant_name}%")

            if min_lease_value is not None:
                param_count += 1
                conditions.append(f"annual_rent >= ${param_count}")
                params.append(min_lease_value)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            param_count += 1

            query = f"""
                SELECT
                    tenant_id,
                    property_id,
                    tenant_name,
                    lease_start_date,
                    lease_end_date,
                    annual_rent,
                    security_deposit,
                    square_footage,
                    tenant_improvements,
                    credit_rating
                FROM tenant_leases
                WHERE {where_clause}
                ORDER BY annual_rent DESC
                LIMIT ${param_count}
            """
            params.append(limit)

            return await self.execute_query(query, tuple(params))

        except Exception as e:
            raise RDSError(f"Error querying tenant information: {e}")

    async def get_debt_terms(
        self,
        loan_type: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_ltv: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query debt terms and conditions.

        Args:
            loan_type: Optional loan type filter
            min_amount: Minimum loan amount
            max_ltv: Maximum loan-to-value ratio
            limit: Maximum number of results

        Returns:
            List of debt terms
        """
        try:
            conditions = []
            params = []
            param_count = 0

            if loan_type:
                param_count += 1
                conditions.append(f"loan_type = ${param_count}")
                params.append(loan_type)

            if min_amount is not None:
                param_count += 1
                conditions.append(f"loan_amount >= ${param_count}")
                params.append(min_amount)

            if max_ltv is not None:
                param_count += 1
                conditions.append(f"ltv_ratio <= ${param_count}")
                params.append(max_ltv)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            param_count += 1

            query = f"""
                SELECT
                    loan_id,
                    loan_type,
                    loan_amount,
                    interest_rate,
                    term_years,
                    ltv_ratio,
                    debt_service_coverage,
                    origination_fee,
                    prepayment_penalty,
                    last_updated
                FROM debt_market_terms
                WHERE {where_clause}
                ORDER BY interest_rate ASC
                LIMIT ${param_count}
            """
            params.append(limit)

            return await self.execute_query(query, tuple(params))

        except Exception as e:
            raise RDSError(f"Error querying debt terms: {e}")

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is accessible
        """
        try:
            result = await self.execute_query("SELECT 1 as health_check", fetch_all=False)
            return len(result) > 0 and result[0].get("health_check") == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
