"""AWS Textract client for document parsing and OCR."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
import time

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mavik_common.errors import (
    TextractError,
    AWSServiceError,
)

logger = logging.getLogger(__name__)


class TextractClient:
    """AWS Textract client for document analysis and OCR."""

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize Textract client.

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
            self.client = self.session.client("textract")

        except NoCredentialsError as e:
            raise AWSServiceError(f"AWS credentials not found: {e}")
        except Exception as e:
            raise AWSServiceError(f"Failed to initialize Textract client: {e}")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def detect_document_text(
        self,
        document: Union[bytes, Dict[str, str]],
    ) -> Dict[str, Any]:
        """Detect text in a document (synchronous operation).

        Args:
            document: Document as bytes or S3 reference {"S3Object": {"Bucket": "...", "Name": "..."}}

        Returns:
            Textract response with detected text

        Raises:
            TextractError: For Textract-specific errors
        """
        try:
            if isinstance(document, bytes):
                document_input = {"Bytes": document}
            else:
                document_input = document

            logger.info("Starting Textract text detection")

            response = self.client.detect_document_text(Document=document_input)

            # Extract text blocks
            text_blocks = response.get("Blocks", [])
            logger.info(f"Detected {len(text_blocks)} text blocks")

            return response

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "InvalidParameterException":
                raise TextractError(f"Invalid document format: {error_msg}")
            elif error_code == "DocumentTooLargeException":
                raise TextractError(f"Document too large: {error_msg}")
            else:
                raise TextractError(f"Textract detect text error: {error_msg}")

        except Exception as e:
            raise TextractError(f"Unexpected error detecting text: {e}")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def analyze_document(
        self,
        document: Union[bytes, Dict[str, str]],
        feature_types: List[str] = None,
        human_loop_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze document for forms and tables (synchronous operation).

        Args:
            document: Document as bytes or S3 reference
            feature_types: List of features to analyze ["TABLES", "FORMS", "SIGNATURES", "LAYOUT"]
            human_loop_config: Optional human review configuration

        Returns:
            Textract response with analysis results

        Raises:
            TextractError: For Textract-specific errors
        """
        try:
            if isinstance(document, bytes):
                document_input = {"Bytes": document}
            else:
                document_input = document

            if feature_types is None:
                feature_types = ["TABLES", "FORMS"]

            kwargs = {
                "Document": document_input,
                "FeatureTypes": feature_types,
            }

            if human_loop_config:
                kwargs["HumanLoopConfig"] = human_loop_config

            logger.info(f"Starting Textract document analysis with features: {feature_types}")

            response = self.client.analyze_document(**kwargs)

            blocks = response.get("Blocks", [])
            logger.info(f"Analyzed {len(blocks)} document blocks")

            return response

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "UnsupportedDocumentException":
                raise TextractError(f"Unsupported document type: {error_msg}")
            else:
                raise TextractError(f"Textract analyze document error: {error_msg}")

        except Exception as e:
            raise TextractError(f"Unexpected error analyzing document: {e}")

    async def start_document_analysis(
        self,
        s3_object: Dict[str, str],
        feature_types: List[str] = None,
        notification_channel: Optional[Dict[str, str]] = None,
        output_config: Optional[Dict[str, Any]] = None,
        job_tag: Optional[str] = None,
    ) -> str:
        """Start asynchronous document analysis.

        Args:
            s3_object: S3 object reference {"Bucket": "...", "Name": "..."}
            feature_types: List of features to analyze
            notification_channel: SNS topic for completion notifications
            output_config: S3 output configuration
            job_tag: Optional job identifier

        Returns:
            Job ID for tracking

        Raises:
            TextractError: For Textract-specific errors
        """
        try:
            if feature_types is None:
                feature_types = ["TABLES", "FORMS"]

            kwargs = {
                "DocumentLocation": {"S3Object": s3_object},
                "FeatureTypes": feature_types,
            }

            if notification_channel:
                kwargs["NotificationChannel"] = notification_channel

            if output_config:
                kwargs["OutputConfig"] = output_config

            if job_tag:
                kwargs["JobTag"] = job_tag

            logger.info(f"Starting async document analysis for {s3_object}")

            response = self.client.start_document_analysis(**kwargs)

            job_id = response["JobId"]
            logger.info(f"Started document analysis job: {job_id}")

            return job_id

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise TextractError(f"Failed to start document analysis: {error_msg}")

        except Exception as e:
            raise TextractError(f"Unexpected error starting document analysis: {e}")

    async def get_document_analysis(
        self,
        job_id: str,
        max_results: Optional[int] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get results from asynchronous document analysis.

        Args:
            job_id: Job ID from start_document_analysis
            max_results: Maximum number of results to return
            next_token: Token for pagination

        Returns:
            Analysis results

        Raises:
            TextractError: For Textract-specific errors
        """
        try:
            kwargs = {"JobId": job_id}

            if max_results:
                kwargs["MaxResults"] = max_results

            if next_token:
                kwargs["NextToken"] = next_token

            logger.debug(f"Getting document analysis results for job: {job_id}")

            response = self.client.get_document_analysis(**kwargs)

            job_status = response.get("JobStatus")
            logger.debug(f"Job status: {job_status}")

            return response

        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise TextractError(f"Failed to get document analysis: {error_msg}")

        except Exception as e:
            raise TextractError(f"Unexpected error getting document analysis: {e}")

    async def wait_for_job_completion(
        self,
        job_id: str,
        max_wait_time: int = 300,
        check_interval: int = 10,
    ) -> Dict[str, Any]:
        """Wait for asynchronous job to complete.

        Args:
            job_id: Job ID to monitor
            max_wait_time: Maximum time to wait in seconds
            check_interval: How often to check status in seconds

        Returns:
            Final job results

        Raises:
            TextractError: If job fails or times out
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                response = await self.get_document_analysis(job_id)
                status = response.get("JobStatus")

                if status == "SUCCEEDED":
                    logger.info(f"Job {job_id} completed successfully")
                    return response
                elif status == "FAILED":
                    error_msg = response.get("StatusMessage", "Job failed")
                    raise TextractError(f"Job {job_id} failed: {error_msg}")
                elif status in ["IN_PROGRESS", "PARTIAL_SUCCESS"]:
                    logger.debug(f"Job {job_id} status: {status}")
                    await asyncio.sleep(check_interval)
                else:
                    raise TextractError(f"Unknown job status: {status}")

            except Exception as e:
                if isinstance(e, TextractError):
                    raise
                logger.error(f"Error checking job status: {e}")
                await asyncio.sleep(check_interval)

        raise TextractError(f"Job {job_id} timed out after {max_wait_time} seconds")

    def extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract plain text from Textract blocks.

        Args:
            blocks: List of Textract blocks

        Returns:
            Extracted text as string
        """
        text_lines = []

        for block in blocks:
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "")
                if text.strip():
                    text_lines.append(text)

        return "\n".join(text_lines)

    def extract_tables_from_blocks(self, blocks: List[Dict[str, Any]]) -> List[List[List[str]]]:
        """Extract tables from Textract blocks.

        Args:
            blocks: List of Textract blocks

        Returns:
            List of tables, each table is a list of rows, each row is a list of cells
        """
        tables = []

        # Create lookup for blocks by ID
        block_map = {block["Id"]: block for block in blocks}

        # Find table blocks
        for block in blocks:
            if block.get("BlockType") == "TABLE":
                table = self._extract_table_data(block, block_map)
                if table:
                    tables.append(table)

        return tables

    def _extract_table_data(self, table_block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]) -> List[List[str]]:
        """Extract data from a single table block."""
        rows = {}

        # Get relationships for this table
        relationships = table_block.get("Relationships", [])

        for relationship in relationships:
            if relationship.get("Type") == "CHILD":
                for child_id in relationship.get("Ids", []):
                    cell_block = block_map.get(child_id)
                    if cell_block and cell_block.get("BlockType") == "CELL":
                        row_index = cell_block.get("RowIndex", 0)
                        col_index = cell_block.get("ColumnIndex", 0)

                        if row_index not in rows:
                            rows[row_index] = {}

                        # Extract cell text
                        cell_text = ""
                        cell_relationships = cell_block.get("Relationships", [])
                        for cell_rel in cell_relationships:
                            if cell_rel.get("Type") == "CHILD":
                                for word_id in cell_rel.get("Ids", []):
                                    word_block = block_map.get(word_id)
                                    if word_block and word_block.get("BlockType") == "WORD":
                                        if cell_text:
                                            cell_text += " "
                                        cell_text += word_block.get("Text", "")

                        rows[row_index][col_index] = cell_text

        # Convert to list of lists
        if not rows:
            return []

        max_row = max(rows.keys())
        max_col = max(max(row.keys()) if row else [0] for row in rows.values())

        table_data = []
        for row_idx in range(1, max_row + 1):  # Textract uses 1-based indexing
            row_data = []
            for col_idx in range(1, max_col + 1):
                cell_text = rows.get(row_idx, {}).get(col_idx, "")
                row_data.append(cell_text)
            table_data.append(row_data)

        return table_data

    def extract_key_value_pairs(self, blocks: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extract key-value pairs from form data.

        Args:
            blocks: List of Textract blocks

        Returns:
            Dictionary of key-value pairs
        """
        key_value_pairs = {}

        # Create lookup for blocks by ID
        block_map = {block["Id"]: block for block in blocks}

        # Find key-value set blocks
        for block in blocks:
            if (block.get("BlockType") == "KEY_VALUE_SET" and
                block.get("EntityTypes") and
                "KEY" in block.get("EntityTypes", [])):

                key_text = self._extract_text_from_block(block, block_map)
                value_text = ""

                # Find associated value
                relationships = block.get("Relationships", [])
                for relationship in relationships:
                    if relationship.get("Type") == "VALUE":
                        for value_id in relationship.get("Ids", []):
                            value_block = block_map.get(value_id)
                            if value_block:
                                value_text = self._extract_text_from_block(value_block, block_map)
                                break

                if key_text:
                    key_value_pairs[key_text] = value_text

        return key_value_pairs

    def _extract_text_from_block(self, block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]) -> str:
        """Extract text content from a block and its children."""
        text_parts = []

        relationships = block.get("Relationships", [])
        for relationship in relationships:
            if relationship.get("Type") == "CHILD":
                for child_id in relationship.get("Ids", []):
                    child_block = block_map.get(child_id)
                    if child_block and child_block.get("BlockType") == "WORD":
                        text_parts.append(child_block.get("Text", ""))

        return " ".join(text_parts)
