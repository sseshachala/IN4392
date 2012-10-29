import os
import time
import boto
import boto.ec2
import boto.manage.cmdshell

#The function is based on ec2_launch_instance.py from Python and AWS Cookbook
from utils import aws_utils, static

def launch_instance():
    """
    Launch an instance and wait for it to start running.
    Returns a tuple consisting of the Instance object and the CmdShell object,
    if request, or None.
    """
    config = aws_utils.read_config()

    # Create a connection to EC2 service (assuming credentials are in boto config)
    ec2 = boto.ec2.connect_to_region(config.get('environment','region'))

    # Check to see if specified key pair already exists.
    # If we get an InvalidKeyPair.NotFound error back from EC2,
    # it means that it doesn't exist and we need to create it.
    key_name = config.get('environment','key_name')
    try:
        key = ec2.get_all_key_pairs(keynames=[key_name])[0]
    except ec2.ResponseError, e:
        if e.code == 'InvalidKeyPair.NotFound':
            print 'Creating keypair: %s' % key_name
            # Create an SSH key to use when logging into instances.
            key = ec2.create_key_pair(key_name)

            # AWS will store the public key but the private key is
            # generated and returned and needs to be stored locally.
            # The save method will also chmod the file to protect
            # your private key.
            key.save(static.KEY_DIR)
        else:
            raise

    # Check to see if specified security group already exists.
    # If we get an InvalidGroup.NotFound error back from EC2,
    # it means that it doesn't exist and we need to create it.
    try:
        group = ec2.get_all_security_groups(groupnames=[static.SECURITY_GROUP_NAME])[0]
    except ec2.ResponseError, e:
        if e.code == 'InvalidGroup.NotFound':
            print 'Creating Security Group: %s' % static.SECURITY_GROUP_NAME
            # Create a security group to control access to instance via SSH.
            group = ec2.create_security_group(static.SECURITY_GROUP_NAME,
                'A group that allows SSH access')
        else:
            raise

    # Add a rule to the security group to authorize SSH traffic on the specified port.
    try:
        group.authorize('tcp', static.SSH_PORT, static.SSH_PORT, static.CIDR)
        group.authorize('tcp', static.HTTPD_PORT, static.HTTPD_PORT, static.CIDR)
    except ec2.ResponseError, e:
        if e.code == 'InvalidPermission.Duplicate':
            print 'Security Group %s already authorized' % static.SECURITY_GROUP_NAME
        else:
            raise

    # Now start up the instance.  The run_instances method
    # has many, many parameters but these are all we need
    # for now.
    reservation = ec2.run_instances(config.get('environment','ami'),
        key_name=key_name,
        security_groups=[static.SECURITY_GROUP_NAME],
        instance_type=config.get('environment', 'instance_type'))

    # Find the actual Instance object inside the Reservation object
    # returned by EC2.
    instance = reservation.instances[0]

    # The instance has been launched but it's not yet up and
    # running.  Let's wait for it's state to change to 'running'.
    print 'Launching AWS EC2 instance'
    while instance.state != 'running':
        time.sleep(5)
        instance.update()
    print instance.public_dns_name + " started"

    # Let's tag the instance with the specified label so we can
    # identify it later.
    #instance.add_tag(static.)
    print 'Connecting to the newly created instance'
    time.sleep(45) #empirically determined value which is sufficied for the instance to accept ssh connection
    key_path = os.path.join(os.path.expanduser(static.KEY_DIR), key_name+static.KEY_EXTENSION)
    cmd = boto.manage.cmdshell.sshclient_from_instance(instance, key_path, user_name= 'ec2-user')
    return instance, cmd

def terminate_instances(instances_to_terminate):
    config = aws_utils.read_config()

    # Create a connection to EC2 service (assuming credentials are in boto config)
    ec2 = boto.ec2.connect_to_region(config.get('environment','region'))
    running_instances = ec2.get_all_instances(filters = {'instance-state-name':'running'})[0].instances

    for instance in running_instances:
        if instance.id in instances_to_terminate:
            instance.terminate()
            print 'AWS EC2 instance %s terminated' % instance.id

