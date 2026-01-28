import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export interface AuthStackProps extends cdk.StackProps {
  projectName: string;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    // Create Cognito User Pool
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `${props.projectName}-users`,
      selfSignUpEnabled: false, // Admin-only signup for compliance
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
        fullname: {
          required: true,
          mutable: true,
        },
      },
      customAttributes: {
        role: new cognito.StringAttribute({ mutable: true }),
        department: new cognito.StringAttribute({ mutable: true }),
      },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      mfa: cognito.Mfa.OPTIONAL,
      mfaSecondFactor: {
        sms: true,
        otp: true,
      },
    });

    // Create App Client
    this.userPoolClient = this.userPool.addClient('AppClient', {
      userPoolClientName: `${props.projectName}-app`,
      authFlows: {
        userSrp: true,
        userPassword: true,
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
        callbackUrls: ['http://localhost:5173/callback', 'https://your-domain.com/callback'],
        logoutUrls: ['http://localhost:5173', 'https://your-domain.com'],
      },
      preventUserExistenceErrors: true,
    });

    // Create User Pool Groups for role-based access
    new cognito.CfnUserPoolGroup(this, 'AnalystGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Analysts',
      description: 'Compliance analysts with standard access',
    });

    new cognito.CfnUserPoolGroup(this, 'SupervisorGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Supervisors',
      description: 'Compliance supervisors with elevated access',
    });

    new cognito.CfnUserPoolGroup(this, 'AdminGroup', {
      userPoolId: this.userPool.userPoolId,
      groupName: 'Admins',
      description: 'System administrators with full access',
    });

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });
  }
}
