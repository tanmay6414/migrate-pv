import sys
import os
import json
import boto3
conn = boto3.client('ec2', region_name='us-east-2')


namespace = "my-namespace"
backup_name="migrate-"+namespace

#Copy snapshot from us-east-1 to us-east-2 with new kms key
def copysnap(snaplists):
    vollist=[]
    for snapshots in snaplist:
        voldict ={}
        snapAZ = ""
        if snapshots["region"] == "us-east-1a":
            snapAZ = "us-east-2a"
        elif snapshots["region"] == "us-east-1b":
            snapAZ = "us-east-2b"
        else:
            snapAZ = "us-east-2c"
        print('Copying Snapshot -> ' + snapshots["snapid"])
        response = conn.copy_snapshot(
        Description='Snapshot copied from us-east-1 my-namespace ' + snapshots["snapid"],
        DestinationRegion='us-east-2',
        SourceRegion='us-east-1',
        Encrypted=True,
        KmsKeyId='ab469db8-89ab-4822-7ce1-dd4420a94c83',
        TagSpecifications=[
        {
            'ResourceType': 'snapshot',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'copy-snapshot-'+snapshots["snapid"]
                },
            ]
        },],
        SourceSnapshotId=snapshots["snapid"],)
        voldict["snapid"] = response["SnapshotId"]
        voldict["region"] = snapAZ
        voldict["kubernetes.io/created-for/pvc/name"]=snapshots["kubernetes.io/created-for/pvc/name"]
        vollist.append(voldict)
        break

    print("\n")
    print(vollist)
    print("\n Copy this Dict and assign it to \"volumelist\" variable")

def readbackup(namespace, backup_name)
    filename=namespace+"/"+backup_name+"-volumesnapshots"
    f = open(filename+".json")
    data = json.load(f)
    snaplist = []

    for i in data:
        intersnapdict = {}
        tags = {}
        intersnapdict["snapid"]=i["status"]["providerSnapshotID"]
        intersnapdict["region"]=i["spec"]["volumeAZ"]
        volume = ec2.Volume(i['spec']['providerVolumeID'])
        for j in volume.tags:
            if j["Key"] == "kubernetes.io/created-for/pvc/name":
                intersnapdict["kubernetes.io/created-for/pvc/name"] = j["Value"]
        snaplist.append(intersnapdict)
    print(snaplist)
    print("\n\n\n")
    f.close()
    # #This will copy snapshot
    copysnap(snaplist)
    
readbackup(namespace, backup_name)

