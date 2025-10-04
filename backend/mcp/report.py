from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import List, Dict, Any
import boto3
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

class ReportGenerator:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.bucket = os.getenv('S3_BUCKET_REPORTS', 'mavik-reports')

    async def generate_docx(
        self,
        sections: List[Dict[str, Any]],
        title: str = "Pre-Screening Analysis"
    ) -> str:
        """Generate Word document with 1\" margins and proper formatting"""

        doc = Document()

        # Set 1" margins
        sections_obj = doc.sections
        for section in sections_obj:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Add title
        heading = doc.add_heading(title, 0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add each section
        for section in sections:
            # Section title
            doc.add_heading(section['title'], level=1)

            # Section content
            content_para = doc.add_paragraph(section['content'])
            content_para.paragraph_format.space_after = Pt(12)

        # Save to temp file
        temp_filename = f"/tmp/{uuid.uuid4()}.docx"
        doc.save(temp_filename)

        # Upload to S3
        s3_key = f"reports/{uuid.uuid4()}.docx"
        self.s3_client.upload_file(temp_filename, self.bucket, s3_key)

        # Generate presigned URL (valid for 7 days)
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': s3_key},
            ExpiresIn=604800  # 7 days
        )

        # Clean up temp file
        os.remove(temp_filename)

        return url

# Global instance
report_generator = ReportGenerator()

async def generate_docx(sections: List[Dict[str, Any]], title: str = "Pre-Screening Analysis") -> str:
    return await report_generator.generate_docx(sections, title)
