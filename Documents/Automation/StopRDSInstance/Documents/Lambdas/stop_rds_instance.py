#
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import json
import re
from datetime import datetime

import boto3

SNAPSHOT_ID = "DBSnapshotIdentifier"
DB_INST_ID = "DBInstanceIdentifier"

INST_ID = "db-instance-id"
ISO_DATE = "iso-date"
ISO_DATETIME = "iso-datetime"
ISO_TIME = "iso-time"
SNAP_ID = "db-snapshot-id"
EXECUTION_ID = "execution-id"

PH_TAG_VAL_STR = "{{{}}}"
TAG_SHORTCUT_EXPR = "Key=(.+),\s*Value=(.*)"


def parse_tags(tags_str):
    if re.match("({};?)+".format(TAG_SHORTCUT_EXPR), tags_str):
        matches = [re.match(TAG_SHORTCUT_EXPR, t.strip()) for t in tags_str.split(";")]
        return [{"Key": m.group(1), "Value": m.group(2) if m.lastindex > 1 else ""} for m in matches]
    else:
        return json.loads(tags_str)


def build_tags(tag_str, context, tag_vars=None):
    if tag_str == "":
        return []

    placeholders = tag_data(ctx=context, tag_vars=tag_vars)
    tags = parse_tags(tag_str)

    for tag in tags:
        value = tag.get("Value")
        for p in placeholders:
            value = value.replace(PH_TAG_VAL_STR.format(p), str(placeholders[p]))
        tag["Value"] = value
    return tags


def template_string(s, context, str_vars=None):
    if s == "":
        return ""

    snapshot_id = s
    placeholders = tag_data(ctx=context, tag_vars=str_vars)
    for p in placeholders:
        snapshot_id = snapshot_id.replace(PH_TAG_VAL_STR.format(p), str(placeholders[p]))
    return snapshot_id


def tag_data(ctx, tag_vars):
    dt = datetime.now().replace(microsecond=0)
    data = {
        ISO_DATETIME: dt.isoformat(),
        ISO_DATE: dt.date().isoformat(),
        ISO_TIME: dt.time().isoformat(),
        EXECUTION_ID: "-".join(ctx.function_name.split("-")[-5:]) if ctx is not None else ""
    }

    if tag_vars is not None:
        for t in tag_vars:
            data[t] = tag_vars[t]

    return data


def handler(event, context):
    debug = False

    try:
        debug = event.get("Debug", False)

        client = boto3.client('rds')

        inst_id = event[DB_INST_ID]
        snapshot_str = event.get(SNAPSHOT_ID, "").strip()
        overwrite_snapshot = event.get("OverwriteExistingSnapshot", "false").lower() == "true"

        args = {
            DB_INST_ID: inst_id
        }

        tag_vars = {INST_ID: inst_id}

        if snapshot_str != "":
            snapshot_id = template_string(snapshot_str, context, tag_vars)
            args[SNAPSHOT_ID] = snapshot_id

            if overwrite_snapshot:
                try:
                    client.delete_db_snapshot(DBSnapshotIdentifier=snapshot_id)
                except Exception as ex:
                    if type(ex).__name__ != "DBSnapshotNotFoundFault":
                        raise ex
        else:
            snapshot_id = ""

        tag_vars[SNAP_ID] = snapshot_id
        response = client.stop_db_instance(**args)
        db_arn = response["DBInstance"]["DBInstanceArn"]

        inst_tags = build_tags(event.get("StoppedInstanceTags", ""), context, tag_vars)
        if len(inst_tags) != 0:
            client.add_tags_to_resource(ResourceName=db_arn, Tags=inst_tags)

        snapshot_tags = build_tags(event.get("SnapshotTags", ""), context, tag_vars)
        if len(snapshot_tags) > 0 and snapshot_str != "":
            snapshot_arn = "{}:snapshot:{}".format(":".join(db_arn.split(":")[0:5]), snapshot_id)
            client.add_tags_to_resource(ResourceName=snapshot_arn, Tags=snapshot_tags)

        return {
            SNAPSHOT_ID: snapshot_id,
        }
    except Exception as ex:
        if not debug:
            raise ex
        return {
            "error": ex.message,
        }
