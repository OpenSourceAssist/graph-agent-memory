import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface MonitoringStackProps extends cdk.StackProps {
  projectName: string;
  apiGateway: apigateway.RestApi;
  lambdaFunction: lambda.Function;
}

export class MonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    // CloudWatch Dashboard
    const dashboard = new cloudwatch.Dashboard(this, 'Dashboard', {
      dashboardName: `${props.projectName}-dashboard`,
    });

    // API Gateway Metrics
    const apiRequests = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: 'Count',
      dimensionsMap: {
        ApiName: props.apiGateway.restApiName,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    const apiLatency = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: 'Latency',
      dimensionsMap: {
        ApiName: props.apiGateway.restApiName,
      },
      statistic: 'Average',
      period: cdk.Duration.minutes(5),
    });

    const api4xxErrors = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: '4XXError',
      dimensionsMap: {
        ApiName: props.apiGateway.restApiName,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    const api5xxErrors = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: '5XXError',
      dimensionsMap: {
        ApiName: props.apiGateway.restApiName,
      },
      statistic: 'Sum',
      period: cdk.Duration.minutes(5),
    });

    // Lambda Metrics
    const lambdaInvocations = props.lambdaFunction.metricInvocations({
      period: cdk.Duration.minutes(5),
    });

    const lambdaErrors = props.lambdaFunction.metricErrors({
      period: cdk.Duration.minutes(5),
    });

    const lambdaDuration = props.lambdaFunction.metricDuration({
      period: cdk.Duration.minutes(5),
    });

    const lambdaThrottles = props.lambdaFunction.metricThrottles({
      period: cdk.Duration.minutes(5),
    });

    // Add widgets to dashboard
    dashboard.addWidgets(
      new cloudwatch.TextWidget({
        markdown: '# Financial Services Advisor - Operations Dashboard',
        width: 24,
        height: 1,
      })
    );

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Gateway - Request Count',
        left: [apiRequests],
        width: 8,
      }),
      new cloudwatch.GraphWidget({
        title: 'API Gateway - Latency (ms)',
        left: [apiLatency],
        width: 8,
      }),
      new cloudwatch.GraphWidget({
        title: 'API Gateway - Errors',
        left: [api4xxErrors, api5xxErrors],
        width: 8,
      })
    );

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda - Invocations',
        left: [lambdaInvocations],
        width: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda - Errors',
        left: [lambdaErrors],
        width: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda - Duration (ms)',
        left: [lambdaDuration],
        width: 6,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda - Throttles',
        left: [lambdaThrottles],
        width: 6,
      })
    );

    // Alarms
    // High error rate alarm
    new cloudwatch.Alarm(this, 'HighErrorRateAlarm', {
      alarmName: `${props.projectName}-high-error-rate`,
      alarmDescription: 'API error rate exceeds threshold',
      metric: api5xxErrors,
      threshold: 10,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });

    // High latency alarm
    new cloudwatch.Alarm(this, 'HighLatencyAlarm', {
      alarmName: `${props.projectName}-high-latency`,
      alarmDescription: 'API latency exceeds threshold',
      metric: apiLatency,
      threshold: 5000, // 5 seconds
      evaluationPeriods: 3,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });

    // Lambda errors alarm
    new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
      alarmName: `${props.projectName}-lambda-errors`,
      alarmDescription: 'Lambda function errors detected',
      metric: lambdaErrors,
      threshold: 5,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });

    // Outputs
    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${props.projectName}-dashboard`,
      description: 'CloudWatch Dashboard URL',
    });
  }
}
