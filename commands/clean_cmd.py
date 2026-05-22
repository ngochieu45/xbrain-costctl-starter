"""clean — (stretch) bulk terminate resources matching a tag.

WARNING — DESIGN-FOR-SAFETY
---------------------------
This is the most dangerous command in the CLI. Get the contract right:

  1. DEFAULT IS DRY-RUN. Without --apply the command MUST NOT touch resources.
     It only lists what WOULD be deleted.
  2. Even with --apply, you should consider printing a summary count first
     ("about to terminate N EC2 + M volumes — proceed?"), though for this
     starter a hard `--apply` flag is enough.
  3. Never use this with a tag you don't fully own. Reflection prompt in
     README covers the blast-radius scenario.

WHAT YOU MUST BUILD
-------------------
1. `_find_targets(tag_key, tag_val)` — return a dict like:
     {"ec2": [<instance ids in non-terminal state>],
      "volume": [<volume ids in 'available' state only>]}
   Skip terminated/shutting-down instances (already gone).
   Skip in-use volumes (can't delete while attached — would error anyway).

2. `run(args)` — call _find_targets, print the plan, then either:
     - bail with "(dry-run — pass --apply to ...)"  (default)
     - or actually terminate (when --apply)

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)

AWS APIS YOU'LL NEED
--------------------
- ec2.describe_instances() + describe_volumes() — same as list_cmd
- ec2.terminate_instances(InstanceIds=[...])
- ec2.delete_volume(VolumeId=...)  (per volume, no bulk API)

VERIFY
------
    pytest tests/test_clean.py -v
"""

import boto3

from commands._common import parse_kv, tags_to_dict


def _find_targets(tag_key, tag_val):
    ec2 = boto3.client("ec2")

    targets = {
        "ec2": [],
        "volume": [],
    }

    paginator = ec2.get_paginator("describe_instances")

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:

                state = instance["State"]["Name"]

                if state in ["terminated", "shutting-down"]:
                    continue

                tags = tags_to_dict(instance.get("Tags", []))

                if tags.get(tag_key) == tag_val:
                    targets["ec2"].append(instance["InstanceId"])

    vpaginator = ec2.get_paginator("describe_volumes")

    for page in vpaginator.paginate():
        for volume in page["Volumes"]:

            if volume["State"] != "available":
                continue

            tags = tags_to_dict(volume.get("Tags", []))

            if tags.get(tag_key) == tag_val:
                targets["volume"].append(volume["VolumeId"])

    return targets


def run(args):
    tag_key, tag_val = parse_kv(args.tag)

    targets = _find_targets(tag_key, tag_val)

    ec2_targets = targets["ec2"]
    volume_targets = targets["volume"]

    if not ec2_targets and not volume_targets:
        print("Nothing to clean.")
        return

    print(f"EC2 targets: {ec2_targets}")
    print(f"Volume targets: {volume_targets}")

    if not args.apply:
        print("(dry-run — pass --apply to actually delete)")
        return

    ec2 = boto3.client("ec2")

    if ec2_targets:
        ec2.terminate_instances(
            InstanceIds=ec2_targets
        )
        print(f"Terminated {len(ec2_targets)} EC2 instance(s)")

    for vid in volume_targets:
        ec2.delete_volume(
            VolumeId=vid
        )
        print(f"Deleted volume {vid}")

    print("Cleanup applied.")




