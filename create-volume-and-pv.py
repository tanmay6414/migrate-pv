import sys
import os
import json
import boto3
conn = boto3.client('ec2', region_name='us-east-2')
ec2 = boto3.resource('ec2',region_name='us-east-1')

#You also need to set your local context to cluster-2

#This will create pvc's
def createpv(volid,size,az,name,namespace):
    start = """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: """+namespace+"""eks-pv-"""+volid+"""
  namespace: """+namespace+"""-new
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
                        'Value': namespace+'eks'
                    },
                ]
            },],
        MultiAttachEnabled=False,)
        print(volume)

        createpv(volume["VolumeId"],str(volume["Size"]), volume["AvailabilityZone"],vol["kubernetes.io/created-for/pvc/name"],namespace)
        
namespace = "my-namespace"
# You must set volumelist variable to the list which you get from step-2
volumelist=[]
creatvol(volumelist,namespace)
        
        
        
        
