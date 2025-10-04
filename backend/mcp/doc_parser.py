import boto3
import os
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

class DocumentParser:
    def __init__(self):
        self.textract = boto3.client(
            'textract',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

    async def extract_pdf_text(self, s3_url: str) -> Dict[str, Any]:
        """Extract text and tables from PDF using AWS Textract"""

        # Parse S3 URL
        # s3://bucket-name/key
        parts = s3_url.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1]

        # Start document analysis
        response = self.textract.start_document_analysis(
            DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}},
            FeatureTypes=['TABLES']
        )

        job_id = response['JobId']

        # Wait for job to complete
        while True:
            response = self.textract.get_document_analysis(JobId=job_id)
            status = response['JobStatus']

            if status in ['SUCCEEDED', 'FAILED']:
                break

        if status == 'FAILED':
            raise Exception('Textract job failed')

        # Extract text and tables
        text = []
        tables = []

        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text.append(block.get('Text', ''))
            elif block['BlockType'] == 'TABLE':
                tables.append(self._extract_table(block, response['Blocks']))

        return {
            'text': '\n'.join(text),
            'tables': tables
        }

    def _extract_table(self, table_block: Dict, all_blocks: List[Dict]) -> Dict:
        """Extract table structure from Textract blocks"""

        table_data = []
        block_map = {block['Id']: block for block in all_blocks}

        for relationship in table_block.get('Relationships', []):
            if relationship['Type'] == 'CHILD':
                for cell_id in relationship['Ids']:
                    cell = block_map.get(cell_id)
                    if cell and cell['BlockType'] == 'CELL':
                        row_index = cell.get('RowIndex', 0)
                        col_index = cell.get('ColumnIndex', 0)

                        # Ensure table_data has enough rows
                        while len(table_data) <= row_index:
                            table_data.append([])

                        # Ensure row has enough columns
                        while len(table_data[row_index]) <= col_index:
                            table_data[row_index].append('')

                        # Extract cell text
                        cell_text = self._get_cell_text(cell, block_map)
                        table_data[row_index][col_index] = cell_text

        return {'data': table_data}

    def _get_cell_text(self, cell_block: Dict, block_map: Dict) -> str:
        """Get text from a cell"""

        text = ''
        for relationship in cell_block.get('Relationships', []):
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = block_map.get(child_id)
                    if word and word['BlockType'] == 'WORD':
                        text += word.get('Text', '') + ' '

        return text.strip()

# Global instance
doc_parser = DocumentParser()

async def extract_pdf_text(s3_url: str) -> Dict[str, Any]:
    return await doc_parser.extract_pdf_text(s3_url)
