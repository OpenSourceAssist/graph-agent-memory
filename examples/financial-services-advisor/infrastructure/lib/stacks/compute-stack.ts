import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface ComputeStackProps extends cdk.StackProps {
  projectName: string;
  vpc: ec2.Vpc;
  documentBucket: s3.Bucket;
}

export class ComputeStack extends cdk.Stack {
  public readonly apiHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    // Lambda execution role
    const lambdaRole = new iam.Role(this, 'LambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
    });

    // Bedrock permissions
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['*'], // Scope to specific models in production
      })
    );

    // Secrets Manager permissions
    lambdaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['secretsmanager:GetSecretValue'],
        resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:${props.projectName}/*`],
      })
    );

    // S3 permissions
    props.documentBucket.grantReadWrite(lambdaRole);

    // Lambda security group
    const lambdaSg = new ec2.SecurityGroup(this, 'LambdaSg', {
      vpc: props.vpc,
      description: 'Security group for Financial Services Advisor Lambda',
      allowAllOutbound: true,
    });

    // Main API Lambda function
    this.apiHandler = new lambda.Function(this, 'ApiHandler', {
      functionName: `${props.projectName}-api`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash',
            '-c',
            'pip install -r requirements.txt -t /asset-output && cp -r src /asset-output/ && cp handler.py /asset-output/',
          ],
        },
      }),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(120),
      role: lambdaRole,
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [lambdaSg],
      environment: {
        LOG_LEVEL: 'INFO',
        S3_BUCKET_NAME: props.documentBucket.bucketName,
        AWS_REGION: this.region,
        BEDROCK_MODEL_ID: 'anthropic.claude-sonnet-4-20250514-v1:0',
        BEDROCK_EMBEDDING_MODEL_ID: 'amazon.titan-embed-text-v2:0',
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    // Outputs
    new cdk.CfnOutput(this, 'LambdaFunctionArn', {
      value: this.apiHandler.functionArn,
      description: 'API Lambda function ARN',
    });
  }
}
