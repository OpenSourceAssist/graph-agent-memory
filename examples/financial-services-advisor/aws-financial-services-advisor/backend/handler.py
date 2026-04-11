"""AWS Lambda handler for Financial Services Advisor.

Uses Mangum to adapt the FastAPI application for Lambda deployment.
"""

from mangum import Mangum
from src.main import app

# Create the Lambda handler
handler = Mangum(app, lifespan="auto")
