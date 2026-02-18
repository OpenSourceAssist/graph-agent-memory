import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface DataStackProps extends cdk.StackProps {
  projectName: string;
  vpc: ec2.Vpc;
}

export class DataStack extends cdk.Stack {
  public readonly documentBucket: s3.Bucket;
  public readonly neo4jSecret: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);

    // S3 Bucket for document storage (KYC documents, reports, etc.)
    this.documentBucket = new s3.Bucket(this, 'DocumentBucket', {
      bucketName: `${props.projectName}-documents-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      lifecycleRules: [
        {
          // Move to Glacier after 90 days for compliance retention
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
          // Keep for 7 years (typical compliance requirement)
          expiration: cdk.Duration.days(2555),
        },
      ],
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT],
          allowedOrigins: ['http://localhost:5173', 'https://your-domain.com'],
          allowedHeaders: ['*'],
        },
      ],
    });

    // Secret for Neo4j Aura connection
    this.neo4jSecret = new secretsmanager.Secret(this, 'Neo4jSecret', {
      secretName: `${props.projectName}/neo4j-credentials`,
      description: 'Neo4j Aura connection credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          uri: 'neo4j+s://xxxx.databases.neo4j.io',
          username: 'neo4j',
          database: 'neo4j',
        }),
        generateStringKey: 'password',
        excludePunctuation: true,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'DocumentBucketName', {
      value: this.documentBucket.bucketName,
      description: 'Document storage bucket name',
    });

    new cdk.CfnOutput(this, 'Neo4jSecretArn', {
      value: this.neo4jSecret.secretArn,
      description: 'Neo4j credentials secret ARN',
    });
  }
}
