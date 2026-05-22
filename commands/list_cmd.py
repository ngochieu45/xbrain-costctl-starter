"""list — list AWS resources by type, filter by tag / missing-tag.

WHAT YOU MUST BUILD
-------------------
Support 4 resource types: ec2, rds, s3, volume.
Each takes:
- `want` — list of (key, value) tag pairs the resource MUST have
- `missing` — list of tag keys the resource MUST NOT have

Print a formatted table to stdout. Test cases are in tests/test_list.py.

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)            # "Owner=alice" -> ("Owner", "alice")
  tags_to_dict(items) -> dict       # boto3 [{"Key","Value"}] -> {k: v}
  tags_match(tags, want, missing) -> bool

AWS APIS YOU'LL NEED
--------------------
- EC2: ec2.describe_instances() with get_paginator
- RDS: rds.describe_db_instances(), then list_tags_for_resource(ResourceName=arn)
- S3:  s3.list_buckets(), then get_bucket_tagging(Bucket=name)
       (catch ClientError when bucket has no tagging config — treat as {})
- EBS: ec2.describe_volumes() with get_paginator

EXPECTED OUTPUT FORMAT (when run from CLI)
------------------------------------------
    EC2 Environment=dev — 1 found:
    ------------------------------------------------------------------------------
      i-0abc123def456789a       t3.micro       running       Environment=dev

VERIFY
------
    pytest tests/test_list.py -v
"""
import boto3

from commands._common import parse_kv, tags_to_dict, tags_match


def _list_ec2(want, missing):
    """List EC2 instances matching tag filters.

    Args:
        want: list of (key, value) tag pairs that must all match
        missing: list of tag keys that must NOT be present

    Returns:
        list of (instance_id, instance_type, state, tags_dict) tuples
    """
    ec2 = boto3.client("ec2")
    paginator = ec2.get_paginator("describe_instances")
    results = []
    
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                tags = tags_to_dict(instance.get("Tags", []))
                
                if tags_match(tags, want, missing):
                    results.append((
                        instance["InstanceId"],
                        instance["InstanceType"],
                        instance["State"]["Name"],
                        tags
                    ))
    
    return results


def _list_rds(want, missing):
    """Same shape as _list_ec2 but for RDS DB instances.

    Note: RDS tags require a separate API call per DB:
        rds.list_tags_for_resource(ResourceName=db['DBInstanceArn'])

    Returns:
        list of (db_id, db_class, db_status, tags_dict) tuples
    """
    rds = boto3.client("rds")
    results = []
    
    # RDS doesn't have paginator for describe_db_instances in older boto3
    # but we'll handle it safely
    try:
        paginator = rds.get_paginator("describe_db_instances")
        pages = paginator.paginate()
    except:
        # Fallback if paginator not available
        pages = [rds.describe_db_instances()]
    
    for page in pages:
        for db in page["DBInstances"]:
            # Get tags for this DB instance
            tag_response = rds.list_tags_for_resource(
                ResourceName=db["DBInstanceArn"]
            )
            tags = tags_to_dict(tag_response.get("TagList", []))
            
            if tags_match(tags, want, missing):
                results.append((
                    db["DBInstanceIdentifier"],
                    db["DBInstanceClass"],
                    db["DBInstanceStatus"],
                    tags
                ))
    
    return results


def _list_s3(want, missing):
    """List S3 buckets matching tag filters.

    Note: get_bucket_tagging raises ClientError if no tagging config exists
    for that bucket. Treat that as an empty tags dict, not an error.

    Returns:
        list of (bucket_name, "bucket", "active", tags_dict) tuples
    """
    from botocore.exceptions import ClientError
    
    s3 = boto3.client("s3")
    results = []
    
    response = s3.list_buckets()
    for bucket in response.get("Buckets", []):
        bucket_name = bucket["Name"]
        
        # Try to get tags, treat missing tagging config as empty dict
        try:
            tag_response = s3.get_bucket_tagging(Bucket=bucket_name)
            tags = tags_to_dict(tag_response.get("TagSet", []))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchTagSet":
                tags = {}
            else:
                raise
        
        if tags_match(tags, want, missing):
            results.append((
                bucket_name,
                "bucket",
                "active",
                tags
            ))
    
    return results


def _list_volume(want, missing):
    """List EBS volumes matching tag filters.

    Returns:
        list of (volume_id, "<type>-<size>GB", state, tags_dict) tuples
        e.g. ("vol-0abc", "gp2-100GB", "in-use", {"purpose": "practice"})
    """
    ec2 = boto3.client("ec2")
    paginator = ec2.get_paginator("describe_volumes")
    results = []
    
    for page in paginator.paginate():
        for volume in page["Volumes"]:
            tags = tags_to_dict(volume.get("Tags", []))
            
            if tags_match(tags, want, missing):
                volume_type = volume["VolumeType"]
                size = volume["Size"]
                type_size = f"{volume_type}-{size}GB"
                
                results.append((
                    volume["VolumeId"],
                    type_size,
                    volume["State"],
                    tags
                ))
    
    return results


DISPATCH = {
    "ec2": _list_ec2,
    "rds": _list_rds,
    "s3": _list_s3,
    "volume": _list_volume,
}


def run(args):
    """Entry point called by costctl.py.

    Steps you should perform:
      1. Convert args.tag (list of "k=v" strings) → want pairs via parse_kv
      2. Use args.missing_tag (list of keys) as-is
      3. Call DISPATCH[args.type](want, missing) → rows
      4. Print a header line, separator, then one row per resource

    Args set by argparse:
        args.type         — one of "ec2", "rds", "s3", "volume"
        args.tag          — list[str], each "key=value"
        args.missing_tag  — list[str], each "key"
    """
    # 1. Parse tag filters
    want = [parse_kv(t) for t in args.tag]
    missing = args.missing_tag
    
    # 2. Call appropriate function
    rows = DISPATCH[args.type](want, missing)
    
    # 3. Build header
    filter_parts = []
    for k, v in want:
        filter_parts.append(f"{k}={v}")
    for k in missing:
        filter_parts.append(f"missing-{k}")
    
    filter_str = " ".join(filter_parts) if filter_parts else "all"
    type_name = args.type.upper() if args.type != "volume" else "Volume"
    
    print(f"{type_name} {filter_str} — {len(rows)} found:")
    print("-" * 78)
    
    # 4. Print rows
    for row in rows:
        resource_id, resource_type, state, tags = row
        # Format tags as key=value pairs
        tag_str = " ".join(f"{k}={v}" for k, v in sorted(tags.items()))
        print(f"  {resource_id:30s} {resource_type:14s} {state:13s} {tag_str}")
