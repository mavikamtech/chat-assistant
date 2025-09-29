"""AWS S3 client for document storage and retrieval."""

import logging
from typing import Any, Dict, List, Optional, BinaryIO
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mavik_common.errors import (
    S3Error,
    S3ObjectNotFoundError,
    AWSServiceError,
)

logger = logging.getLogger(__name__)


class S3Client:
    """AWS S3 client with retry logic and convenience methods."""
    
    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """Initialize S3 client.
        
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
            self.client = self.session.client("s3")
            
        except NoCredentialsError as e:
            raise AWSServiceError(f"AWS credentials not found: {e}")
        except Exception as e:
            raise AWSServiceError(f"Failed to initialize S3 client: {e}")
    
    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def upload_file(
        self,
        file_path: str,
        bucket_name: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload a file to S3.
        
        Args:
            file_path: Local file path to upload
            bucket_name: S3 bucket name
            s3_key: S3 object key
            metadata: Optional object metadata
            tags: Optional object tags
            
        Returns:
            S3 URI of uploaded object
            
        Raises:
            S3Error: For S3-specific errors
        """
        try:
            extra_args = {}
            
            if metadata:
                extra_args["Metadata"] = metadata
                
            if tags:
                tag_string = "&".join([f"{k}={v}" for k, v in tags.items()])
                extra_args["Tagging"] = tag_string
            
            logger.info(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
            self.client.upload_file(file_path, bucket_name, s3_key, ExtraArgs=extra_args)
            
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Successfully uploaded to {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            
            if error_code == "NoSuchBucket":
                raise S3Error(f"Bucket not found: {bucket_name}")
            else:
                raise S3Error(f"S3 upload error: {error_msg}")
                
        except Exception as e:
            raise S3Error(f"Unexpected error uploading file: {e}")
    
    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def download_file(
        self,
        bucket_name: str,
        s3_key: str,
        local_path: str,
    ) -> str:
        """Download a file from S3.
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            local_path: Local file path to save
            
        Returns:
            Local file path
            
        Raises:
            S3Error: For S3-specific errors
            S3ObjectNotFoundError: If object not found
        """
        try:
            # Create directory if it doesn't exist
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading s3://{bucket_name}/{s3_key} to {local_path}")
            self.client.download_file(bucket_name, s3_key, local_path)
            
            logger.info(f"Successfully downloaded to {local_path}")
            return local_path
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            
            if error_code == "NoSuchKey":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket_name}/{s3_key}")
            elif error_code == "NoSuchBucket":
                raise S3Error(f"Bucket not found: {bucket_name}")
            else:
                raise S3Error(f"S3 download error: {error_msg}")
                
        except Exception as e:
            raise S3Error(f"Unexpected error downloading file: {e}")
    
    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_object(
        self,
        bucket_name: str,
        s3_key: str,
    ) -> bytes:
        """Get object content as bytes.
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            
        Returns:
            Object content as bytes
            
        Raises:
            S3Error: For S3-specific errors
            S3ObjectNotFoundError: If object not found
        """
        try:
            logger.info(f"Getting object s3://{bucket_name}/{s3_key}")
            response = self.client.get_object(Bucket=bucket_name, Key=s3_key)
            
            content = response["Body"].read()
            logger.info(f"Retrieved {len(content)} bytes")
            return content
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            
            if error_code == "NoSuchKey":
                raise S3ObjectNotFoundError(f"Object not found: s3://{bucket_name}/{s3_key}")
            else:
                raise S3Error(f"S3 get object error: {error_msg}")
                
        except Exception as e:
            raise S3Error(f"Unexpected error getting object: {e}")
    
    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def put_object(
        self,
        bucket_name: str,
        s3_key: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Put object content to S3.
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            content: Object content as bytes
            content_type: Optional content type
            metadata: Optional object metadata
            
        Returns:
            S3 URI of object
            
        Raises:
            S3Error: For S3-specific errors
        """
        try:
            kwargs = {
                "Bucket": bucket_name,
                "Key": s3_key,
                "Body": content,
            }
            
            if content_type:
                kwargs["ContentType"] = content_type
                
            if metadata:
                kwargs["Metadata"] = metadata
            
            logger.info(f"Putting object to s3://{bucket_name}/{s3_key}")
            self.client.put_object(**kwargs)
            
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Successfully put object to {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise S3Error(f"S3 put object error: {error_msg}")
                
        except Exception as e:
            raise S3Error(f"Unexpected error putting object: {e}")
    
    async def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> List[Dict[str, Any]]:
        """List objects in S3 bucket.
        
        Args:
            bucket_name: S3 bucket name
            prefix: Object key prefix filter
            max_keys: Maximum number of objects to return
            
        Returns:
            List of object metadata dictionaries
            
        Raises:
            S3Error: For S3-specific errors
        """
        try:
            kwargs = {
                "Bucket": bucket_name,
                "MaxKeys": max_keys,
            }
            
            if prefix:
                kwargs["Prefix"] = prefix
            
            logger.info(f"Listing objects in s3://{bucket_name}/{prefix}")
            response = self.client.list_objects_v2(**kwargs)
            
            objects = response.get("Contents", [])
            logger.info(f"Found {len(objects)} objects")
            return objects
            
        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise S3Error(f"S3 list objects error: {error_msg}")
                
        except Exception as e:
            raise S3Error(f"Unexpected error listing objects: {e}")
    
    async def delete_object(
        self,
        bucket_name: str,
        s3_key: str,
    ) -> bool:
        """Delete an object from S3.
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            
        Returns:
            True if deleted successfully
            
        Raises:
            S3Error: For S3-specific errors
        """
        try:
            logger.info(f"Deleting object s3://{bucket_name}/{s3_key}")
            self.client.delete_object(Bucket=bucket_name, Key=s3_key)
            
            logger.info(f"Successfully deleted object")
            return True
            
        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise S3Error(f"S3 delete object error: {error_msg}")
                
        except Exception as e:
            raise S3Error(f"Unexpected error deleting object: {e}")
    
    async def object_exists(
        self,
        bucket_name: str,
        s3_key: str,
    ) -> bool:
        """Check if an object exists in S3.
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            
        Returns:
            True if object exists
        """
        try:
            self.client.head_object(Bucket=bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return False
            # Re-raise other errors
            raise S3Error(f"Error checking object existence: {e}")
    
    async def generate_presigned_url(
        self,
        bucket_name: str,
        s3_key: str,
        expiration: int = 3600,
        method: str = "get_object",
    ) -> str:
        """Generate a presigned URL for S3 object.
        
        Args:
            bucket_name: S3 bucket name
            s3_key: S3 object key
            expiration: URL expiration in seconds
            method: S3 operation (get_object, put_object)
            
        Returns:
            Presigned URL
            
        Raises:
            S3Error: For S3-specific errors
        """
        try:
            url = self.client.generate_presigned_url(
                method,
                Params={"Bucket": bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            
            logger.info(f"Generated presigned URL for s3://{bucket_name}/{s3_key}")
            return url
            
        except Exception as e:
            raise S3Error(f"Error generating presigned URL: {e}")