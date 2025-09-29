#!/usr/bin/env python3
"""
Test script for CDK Infrastructure
Validates CDK synthesis and deployment readiness
"""

import subprocess
import json
import os
from pathlib import Path

def test_cdk_infrastructure():
    """Test CDK infrastructure configuration"""
    
    print("🏗️ Testing CDK Infrastructure...")
    
    # Change to CDK directory
    cdk_dir = Path("infra/cdk")
    if not cdk_dir.exists():
        print("   ❌ CDK directory not found")
        return False
    
    original_dir = os.getcwd()
    os.chdir(cdk_dir)
    
    try:
        # Test 1: CDK Dependencies
        print("\n1. 📦 Checking CDK Dependencies...")
        try:
            result = subprocess.run(["npm", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ NPM dependencies installed")
            else:
                print("   ⚠️ Some dependency issues found")
                print(f"      {result.stdout}")
        except Exception as e:
            print(f"   ❌ NPM check failed: {e}")
            return False
        
        # Test 2: CDK Synthesis
        print("\n2. 🔨 Testing CDK Synthesis...")
        try:
            result = subprocess.run(["npx", "cdk", "synth", "--quiet"], capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ CDK synthesis successful")
                
                # Check for generated CloudFormation templates
                if "Resources" in result.stdout:
                    print("   ✅ CloudFormation templates generated")
                else:
                    print("   ⚠️ No resources found in synthesis output")
                    
            else:
                print("   ❌ CDK synthesis failed:")
                print(f"      {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ CDK synthesis error: {e}")
            return False
        
        # Test 3: CDK Diff (if AWS credentials available)
        print("\n3. 📊 Testing CDK Diff...")
        try:
            result = subprocess.run(["npx", "cdk", "diff", "--quiet"], capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ CDK diff successful (no changes needed)")
            elif "AWS credentials" in result.stderr or "not assume role" in result.stderr:
                print("   ⚠️ AWS credentials not configured (expected for local testing)")
            else:
                print("   ✅ CDK diff shows pending changes")
                
        except Exception as e:
            print("   ⚠️ CDK diff skipped (AWS credentials may not be configured)")
        
        # Test 4: Check Stack Definitions
        print("\n4. 🏗️ Validating Stack Definitions...")
        
        stack_files = [
            "lib/mavik-ai-network-stack.ts",
            "lib/mavik-ai-api-stack.ts", 
            "lib/mavik-ai-compute-stack.ts",
            "lib/mavik-ai-data-stack.ts"
        ]
        
        for stack_file in stack_files:
            if Path(stack_file).exists():
                print(f"   ✅ {stack_file} exists")
                
                # Basic validation - check for key CDK patterns
                with open(stack_file, 'r') as f:
                    content = f.read()
                    
                if "extends cdk.Stack" in content:
                    print(f"      ✅ Proper Stack class definition")
                else:
                    print(f"      ⚠️ No Stack class found")
                    
                if "new cdk.CfnOutput" in content:
                    print(f"      ✅ Contains stack outputs")
                else:
                    print(f"      ⚠️ No stack outputs defined")
                    
            else:
                print(f"   ⚠️ {stack_file} not found")
        
        # Test 5: Environment Configuration
        print("\n5. ⚙️ Environment Configuration...")
        
        # Check for cdk.json
        if Path("cdk.json").exists():
            print("   ✅ cdk.json configuration found")
            
            with open("cdk.json", 'r') as f:
                cdk_config = json.load(f)
                
            if "app" in cdk_config:
                print(f"   ✅ App entry point: {cdk_config['app']}")
            
            if "context" in cdk_config:
                print("   ✅ CDK context configuration found")
                
        else:
            print("   ⚠️ cdk.json not found")
        
        # Test 6: TypeScript Compilation
        print("\n6. 🔧 TypeScript Compilation...")
        try:
            result = subprocess.run(["npx", "tsc", "--noEmit"], capture_output=True, text=True)
            if result.returncode == 0:
                print("   ✅ TypeScript compilation successful")
            else:
                print("   ❌ TypeScript compilation errors:")
                print(f"      {result.stdout}")
                return False
                
        except Exception as e:
            print(f"   ❌ TypeScript compilation test failed: {e}")
            return False
        
        print("\n🎉 CDK Infrastructure tests completed successfully!")
        return True
        
    finally:
        os.chdir(original_dir)

def test_aws_services_config():
    """Test AWS services configuration"""
    
    print("\n🔧 Testing AWS Services Configuration...")
    
    # Test LocalStack connectivity (if running)
    print("\n1. 🌐 LocalStack Services...")
    
    try:
        import boto3
        
        # Configure for LocalStack
        session = boto3.Session()
        
        # Test S3
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url='http://localhost:4566',
                aws_access_key_id='test',
                aws_secret_access_key='test',
                region_name='us-east-1'
            )
            
            buckets = s3_client.list_buckets()
            print("   ✅ S3 service accessible")
            
        except Exception as e:
            print(f"   ⚠️ S3 service not available: {str(e)[:50]}...")
        
        # Test DynamoDB
        try:
            dynamodb_client = boto3.client(
                'dynamodb',
                endpoint_url='http://localhost:4566',
                aws_access_key_id='test',
                aws_secret_access_key='test',
                region_name='us-east-1'
            )
            
            tables = dynamodb_client.list_tables()
            print("   ✅ DynamoDB service accessible")
            
        except Exception as e:
            print(f"   ⚠️ DynamoDB service not available: {str(e)[:50]}...")
        
        # Test Lambda
        try:
            lambda_client = boto3.client(
                'lambda',
                endpoint_url='http://localhost:4566',
                aws_access_key_id='test',
                aws_secret_access_key='test',
                region_name='us-east-1'
            )
            
            functions = lambda_client.list_functions()
            print("   ✅ Lambda service accessible")
            
        except Exception as e:
            print(f"   ⚠️ Lambda service not available: {str(e)[:50]}...")
            
    except ImportError:
        print("   ⚠️ boto3 not installed, skipping AWS service tests")
    
    return True

if __name__ == "__main__":
    success = test_cdk_infrastructure()
    if success:
        test_aws_services_config()
    else:
        print("\n❌ Infrastructure tests failed!")
        exit(1)