# Stop RDS Instance

## Notes

This will stop a running RDS Instance

## Document Design

Refer to schema.json

Document Steps:
1. aws:createStack - Execute CloudFormation Template to create lambda.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     * Parameters: 
       * LambdaRole: {{LambdaAssumeRole}} - role assumed by lambda to create the snapshot.
       * LambdaName: StopRDSInstanceLambda-{{automation:EXECUTION_ID}}
2. aws:invokeLambdaFunction - Execute Lambda to detach the volume
   * Inputs:
     * FunctionName: StopRDSInstanceLambda-{{automation:EXECUTION_ID}} - Lambda name to use
     * Payload:
        * DBInstanceId: {{DBInstanceId}} - The DBInstanceId ID of the RDS Instance.
        * DBSnapshotIdentifier: {{DBSnapshotIdentifier}} - A description for the RDS snapshot.
        * OverwriteExistingSnapshot: {{OverwriteExistingSnapshot}} - Overwrite existing snapshot.
        * StoppedInstanceTags: {{StoppedInstanceTags}} - Tags to create for the stoped instance in json or shortcut format
        * SnapshotTags:{{SnapshotTags}} - Tags to put on RDS snapshot in json or shortcut format 
        * Debug : {{Debug}} - Set to True to let action continue in case of failures and return error as the result
3. aws:deleteStack - Delete CloudFormation Template.
   * Inputs:
     * StackName: {{DocumentStackName}} - Stack name or Unique ID
     
     
**Tag JSON format**  

[{"Key": "key", "Value": "value},{"Key": "key", "Value": "value}]


**Tag shortcut format**

Key=key,Value=value;Key=key,Value=value
     
**Placeholders**
     
The following subjects can be used as placeholders in the tag values and snapshot name

{iso-date} : iso date when the instance was stopped

{iso-datetime} iso datetime when the instance was stopped

{iso-time} iso time when the instance was stopped

{db-instance-id} : Identifier of the stopped instance

{db-snapshot-id} : Identifier of the optionally created snapshot

{execution-id} : SSM automation execution is

Note that when creating tags only the following characters can be used for tag values on RDS resources a-zA-Z0-9\s_\.:+/=\\@-

## Test script

Python script will:
  1. Create a test stack with the automation assumed role and RDS Instance
  2. Execute automation document to stop RDS instance
  4. Verify that the instance is stopped
  5. Test if RDS snapshot was created
  6. Delete the Instance and RDS snapshot
  7. Clean up test stack
