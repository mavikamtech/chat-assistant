"""AWS DynamoDB client for checkpointing and state management."""

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mavik_common.errors import (
    DynamoDBError,
    AWSServiceError,
)

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """AWS DynamoDB client with retry logic and convenience methods."""

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize DynamoDB client.

        Args:
            region_name: AWS region
            aws_access_key_id: Optional explicit AWS credentials
            aws_secret_access_key: Optional explicit AWS credentials
        """
        self.region_name = region_name

        try:
            session_kwargs = {"region_name": region_name}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs.update({
                    "aws_access_key_id": aws_access_key_id,
                    "aws_secret_access_key": aws_secret_access_key,
                })

            self.session = boto3.Session(**session_kwargs)
            self.client = self.session.client("dynamodb")
            self.resource = self.session.resource("dynamodb")

        except NoCredentialsError as e:
            raise AWSServiceError(f"AWS credentials not found: {e}")
        except Exception as e:
            raise AWSServiceError(f"Failed to initialize DynamoDB client: {e}")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        consistent_read: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get an item from DynamoDB table.

        Args:
            table_name: DynamoDB table name
            key: Primary key of the item
            consistent_read: Whether to use consistent read

        Returns:
            Item dictionary or None if not found

        Raises:
            DynamoDBError: For DynamoDB-specific errors
        """
        try:
            table = self.resource.Table(table_name)

            logger.debug(f"Getting item from {table_name}: {key}")
            response = table.get_item(
                Key=key,
                ConsistentRead=consistent_read,
            )

            item = response.get("Item")
            if item:
                # Convert Decimal to float for JSON serialization
                item = self._convert_decimals(item)
                logger.debug(f"Retrieved item: {item}")
            else:
                logger.debug("Item not found")

            return item

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "ResourceNotFoundException":
                raise DynamoDBError(f"Table not found: {table_name}")
            else:
                raise DynamoDBError(f"DynamoDB get error: {error_msg}")

        except Exception as e:
            raise DynamoDBError(f"Unexpected error getting item: {e}")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def put_item(
        self,
        table_name: str,
        item: Dict[str, Any],
        condition_expression: Optional[str] = None,
    ) -> bool:
        """Put an item into DynamoDB table.

        Args:
            table_name: DynamoDB table name
            item: Item dictionary to store
            condition_expression: Optional condition for put operation

        Returns:
            True if successful

        Raises:
            DynamoDBError: For DynamoDB-specific errors
        """
        try:
            table = self.resource.Table(table_name)

            # Convert floats to Decimal for DynamoDB
            item = self._convert_floats(item)

            kwargs = {"Item": item}
            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression

            logger.debug(f"Putting item to {table_name}: {item}")
            table.put_item(**kwargs)

            logger.debug("Item stored successfully")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "ConditionalCheckFailedException":
                raise DynamoDBError(f"Condition check failed: {condition_expression}")
            else:
                raise DynamoDBError(f"DynamoDB put error: {error_msg}")

        except Exception as e:
            raise DynamoDBError(f"Unexpected error putting item: {e}")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        condition_expression: Optional[str] = None,
        return_values: str = "NONE",
    ) -> Optional[Dict[str, Any]]:
        """Update an item in DynamoDB table.

        Args:
            table_name: DynamoDB table name
            key: Primary key of the item
            update_expression: Update expression
            expression_attribute_names: Attribute name mappings
            expression_attribute_values: Attribute value mappings
            condition_expression: Optional condition for update
            return_values: What to return (NONE, ALL_OLD, UPDATED_OLD, ALL_NEW, UPDATED_NEW)

        Returns:
            Updated item attributes (if return_values != NONE)

        Raises:
            DynamoDBError: For DynamoDB-specific errors
        """
        try:
            table = self.resource.Table(table_name)

            kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ReturnValues": return_values,
            }

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            if expression_attribute_values:
                # Convert floats to Decimal
                kwargs["ExpressionAttributeValues"] = self._convert_floats(
                    expression_attribute_values
                )

            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression

            logger.debug(f"Updating item in {table_name}: {key}")
            response = table.update_item(**kwargs)

            attributes = response.get("Attributes")
            if attributes:
                attributes = self._convert_decimals(attributes)
                logger.debug(f"Updated attributes: {attributes}")

            return attributes

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "ConditionalCheckFailedException":
                raise DynamoDBError(f"Condition check failed: {condition_expression}")
            else:
                raise DynamoDBError(f"DynamoDB update error: {error_msg}")

        except Exception as e:
            raise DynamoDBError(f"Unexpected error updating item: {e}")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def delete_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        condition_expression: Optional[str] = None,
    ) -> bool:
        """Delete an item from DynamoDB table.

        Args:
            table_name: DynamoDB table name
            key: Primary key of the item
            condition_expression: Optional condition for delete

        Returns:
            True if successful

        Raises:
            DynamoDBError: For DynamoDB-specific errors
        """
        try:
            table = self.resource.Table(table_name)

            kwargs = {"Key": key}
            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression

            logger.debug(f"Deleting item from {table_name}: {key}")
            table.delete_item(**kwargs)

            logger.debug("Item deleted successfully")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "ConditionalCheckFailedException":
                raise DynamoDBError(f"Condition check failed: {condition_expression}")
            else:
                raise DynamoDBError(f"DynamoDB delete error: {error_msg}")

        except Exception as e:
            raise DynamoDBError(f"Unexpected error deleting item: {e}")

    async def query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        filter_expression: Optional[str] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query items from DynamoDB table.

        Args:
            table_name: DynamoDB table name
            key_condition_expression: Key condition expression
            expression_attribute_names: Attribute name mappings
            expression_attribute_values: Attribute value mappings
            filter_expression: Optional filter expression
            index_name: Optional GSI/LSI name
            limit: Maximum number of items to return
            scan_index_forward: Query order (True = ascending, False = descending)

        Returns:
            List of items

        Raises:
            DynamoDBError: For DynamoDB-specific errors
        """
        try:
            table = self.resource.Table(table_name)

            kwargs = {
                "KeyConditionExpression": key_condition_expression,
                "ScanIndexForward": scan_index_forward,
            }

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            if expression_attribute_values:
                kwargs["ExpressionAttributeValues"] = self._convert_floats(
                    expression_attribute_values
                )

            if filter_expression:
                kwargs["FilterExpression"] = filter_expression

            if index_name:
                kwargs["IndexName"] = index_name

            if limit:
                kwargs["Limit"] = limit

            logger.debug(f"Querying {table_name}")
            response = table.query(**kwargs)

            items = response.get("Items", [])
            items = [self._convert_decimals(item) for item in items]

            logger.debug(f"Query returned {len(items)} items")
            return items

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise DynamoDBError(f"DynamoDB query error: {error_msg}")

        except Exception as e:
            raise DynamoDBError(f"Unexpected error querying: {e}")

    async def scan(
        self,
        table_name: str,
        filter_expression: Optional[str] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Scan items from DynamoDB table.

        Args:
            table_name: DynamoDB table name
            filter_expression: Optional filter expression
            expression_attribute_names: Attribute name mappings
            expression_attribute_values: Attribute value mappings
            index_name: Optional GSI/LSI name
            limit: Maximum number of items to return

        Returns:
            List of items

        Raises:
            DynamoDBError: For DynamoDB-specific errors
        """
        try:
            table = self.resource.Table(table_name)

            kwargs = {}

            if filter_expression:
                kwargs["FilterExpression"] = filter_expression

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names

            if expression_attribute_values:
                kwargs["ExpressionAttributeValues"] = self._convert_floats(
                    expression_attribute_values
                )

            if index_name:
                kwargs["IndexName"] = index_name

            if limit:
                kwargs["Limit"] = limit

            logger.debug(f"Scanning {table_name}")
            response = table.scan(**kwargs)

            items = response.get("Items", [])
            items = [self._convert_decimals(item) for item in items]

            logger.debug(f"Scan returned {len(items)} items")
            return items

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise DynamoDBError(f"DynamoDB scan error: {error_msg}")

        except Exception as e:
            raise DynamoDBError(f"Unexpected error scanning: {e}")

    def _convert_decimals(self, obj: Any) -> Any:
        """Convert Decimal objects to float for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj

    def _convert_floats(self, obj: Any) -> Any:
        """Convert float objects to Decimal for DynamoDB storage."""
        if isinstance(obj, dict):
            return {k: self._convert_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats(item) for item in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
        else:
            return obj
