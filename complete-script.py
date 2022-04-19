
import sys
import os
import json
import boto3
conn = boto3.client('ec2', region_name='us-east-2')
ec2 = boto3.resource('ec2',region_name='us-east-1')


#This will create pvc's
def createpv(volid,size,az,name,namespace):
    start = """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: """+namespace+"""eks-pv-"""+volid+"""
  namespace: """+namespace+"""-eks
  annotations:
    kubernetes.io/createdby: aws-ebs-dynamic-provisioner
    pv.kubernetes.io/bound-by-controller: "yes"
    pv.kubernetes.io/provisioned-by: kubernetes.io/aws-ebs
  labels:
    failure-domain.beta.kubernetes.io/region: us-east-2
    failure-domain.beta.kubernetes.io/zone: """+az+"""
spec:
  capacity:
    storage: """+size+"""Gi
  accessModes:
    - ReadWriteOnce
  claimRef:
    apiVersion: v1
    kind: PersistentVolumeClaim
    name: """+name+"""
    namespace: """+namespace+"""-eks
  awsElasticBlockStore:
    volumeID: aws://"""+az+"""/"""+volid+"""
    fsType: ext4
  storageClassName: ebs
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: failure-domain.beta.kubernetes.io/region
          operator: In
          values:
          - us-east-2
        - key: failure-domain.beta.kubernetes.io/zone
          operator: In
          values:
          - """+az+"""
  persistentVolumeReclaimPolicy: Delete
"""
    f1 = open("pvc.yaml", "w")
    f1.write(start)
    f1.close()
    os.system("kubectl apply -f pvc.yaml")



#This will create volume from snapshot in another region
def creatvol(volumelist, namespace):
    for vol in volumelist:
        volume = conn.create_volume(
        AvailabilityZone=vol["region"],
        Encrypted=True,
        KmsKeyId='ab469db8-89ab-4822-7ce1-dd4420a94c83',
        SnapshotId=vol["snapid"],
        VolumeType='gp2',
        TagSpecifications=[
            {
                'ResourceType': 'volume',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'vol-from-snap-'+vol['snapid']
                    },
                    {
                        'Key': 'kubernetes.io/cluster/tstk8s_vibrenthealth_com',
                        'Value': 'owned'
                    },
                    {
                        'Key': 'kubernetes.io/created-for/pvc/name',
                        'Value': vol["kubernetes.io/created-for/pvc/name"]
                    },
                    {
                        'Key': 'kubernetes.io/created-for/pvc/namespace',
                        'Value': namespace+'-new'
                    },
                ]
            },],
        MultiAttachEnabled=False,)
        print(volume)

        createpv(volume["VolumeId"],str(volume["Size"]), volume["AvailabilityZone"],vol["kubernetes.io/created-for/pvc/name"],namespace)
        break



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
        Description='Snapshot copied from us-east-1 pmi-edge ' + snapshots["snapid"],
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


def backup(namespace, backup_name):
    os.system("velero backup create "+ backup_name+" --include-namespaces "+namespace+"  --include-resources pv,pvc --wait")
    os.system("mkdir "+namespace+ " && export AWS_PROFILE=admin && aws s3 cp s3://cluster-1-velero-backup/cluster-1/backups/migrate-my-namespace/backups/"+backup_name + " " + namespace +  " --recursive " )
    filename=namespace+"/"+backup_name+"-volumesnapshots"
    os.system("gunzip "+filename+".json.gz")

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


namespace = "my-namespace"
backup_name="migrate-"+namespace"


print("Make sure you export \"lowerenvir\" AWS_PROFILE to ternimal")
print("During backup you must have qak8s(source cluster) context and for create pv funcytion you must have set eks cluster context")
print("1. Take Backup \t 2. Copy Snapshot \t 3. Restore PV from snapshot")
a = int(input("what you want to do "))
if a == 1:
    print("This is one time task you do not need to take backup again and again. You can reuse previous backup")
    backup(namespace, backup_name)
elif a == 2:
    print("This function will read backups files and copy snapshot from this")
    readbackup(namespace, backup_name)
elif a == 3:
    volumelist=[]
    print("Please wait until all the copied snapshots are available in another region it will take some time \nAlso Copy list given by copy snapshot function and assign it to \"volumelist\" variable  1. Yes \t 2. No")
    acc = int(input("Do you wants to procced ? "))
    if acc == 1:
        creatvol(volumelist,namespace)
    else:
        exit()



