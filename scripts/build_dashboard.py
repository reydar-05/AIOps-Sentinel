"""
Build the AIOps Sentinel dashboard as a single local HTML file.

Runs the project's REAL parser, sanitiser, trimmer and classifier on simulated
incidents (AI text and Discord alert are sample output), embeds the results in
dashboard/template.html and writes dashboard/index.html.

    python scripts/build_dashboard.py           # build and open in your browser
    python scripts/build_dashboard.py --no-open # build only

No server needed: index.html is a static file you can also double-click.
"""

import json
import os
import sys
import webbrowser

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
for sub in ("incident_processor", "log_processor", "ai_analyzer", "notification_handler"):
    sys.path.insert(0, os.path.join(ROOT, "lambda", sub))
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("LOG_LEVEL", "ERROR")

from event_parser import parse_event  # noqa: E402
from processor import process  # noqa: E402


def sns(msg):
    return {
        "Records": [
            {"Sns": {"TopicArn": "arn:aws:sns:ap-south-1:000000000000:aiops-alerts-dev", "Message": json.dumps(msg)}}
        ]
    }


def cw(name, reason, dim="AutoScalingGroupName", val="aiops-asg-dev"):
    return sns(
        {
            "AlarmName": name,
            "NewStateValue": "ALARM",
            "OldStateValue": "OK",
            "NewStateReason": reason,
            "StateChangeTime": "2026-01-15T10:30:00Z",
            "Region": "ap-south-1",
            "AWSAccountId": "000000000000",
            "Trigger": {"Dimensions": [{"name": dim, "value": val}]},
        }
    )


ec2 = sns(
    {
        "source": "aws.ec2",
        "detail-type": "EC2 Instance State-change Notification",
        "time": "2026-01-15T10:30:00Z",
        "region": "ap-south-1",
        "account": "000000000000",
        "detail": {"instance-id": "i-0abc123def456789", "state": "stopped"},
    }
)

S = [
    dict(
        key="oom",
        title="High CPU from memory leak",
        trigger="CloudWatch alarm aiops-high-cpu-dev",
        event=cw("aiops-high-cpu-dev", "Threshold Crossed: 2 datapoints [92.5, 88.3] >= 80"),
        logs="\n".join(
            [
                "[10:28:00Z] INFO  Server started on 10.0.1.25:8080",
                "[10:28:30Z] INFO  db connect user=admin password=S3cret! host=ip-10-0-1-99.ap-south-1.compute.internal",
                "[10:29:00Z] ERROR java.lang.OutOfMemoryError: Java heap space (owner: ops@example.com)",
                "[10:29:01Z] ERROR   at com.app.DataProcessor.process(DataProcessor.java:142)",
                "[10:29:30Z] FATAL Process killed by OOM killer",
                "[10:30:00Z] CRITICAL CPU utilization 92.5% for 2 periods",
            ]
        ),
        ai=dict(
            severity="HIGH",
            confidence="HIGH",
            summary="Java heap exhaustion (OutOfMemoryError) in DataProcessor led to the process being OOM-killed.",
            root_cause="Logs show java.lang.OutOfMemoryError: Java heap space at DataProcessor.java:142, followed by 'Process killed by OOM killer'. GC thrashing drove CPU above 90%.",
            actions=[
                "Restart the application service",
                "Raise the JVM heap (-Xmx2g)",
                "Scale the Auto Scaling Group to 3 instances",
            ],
            fix="Fix the memory leak in DataProcessor.process and add a heap-usage alarm.",
        ),
    ),
    dict(
        key="disk",
        title="Disk full on web server",
        trigger="CloudWatch alarm aiops-status-check-failed-dev",
        event=cw(
            "aiops-status-check-failed-dev",
            "StatusCheckFailed >= 1 for 2 datapoints",
            "InstanceId",
            "i-0abc123def456789",
        ),
        logs="\n".join(
            [
                "[10:25:10Z] INFO  httpd: request GET /health 200",
                "[10:27:42Z] ERROR write failed: No space left on device /var/log/httpd/access_log",
                "[10:28:01Z] ERROR httpd: cannot open log file, disk full",
                "[10:29:15Z] WARN  df: /dev/xvda1 at 100% used",
                "[10:30:02Z] ERROR status check failed for i-0abc123def456789 from 10.0.2.14",
            ]
        ),
        ai=dict(
            severity="MEDIUM",
            confidence="HIGH",
            summary="The root volume filled to 100%, so httpd could no longer write its logs.",
            root_cause="'No space left on device' on /var/log/httpd/access_log and 'disk full' from httpd show the root filesystem is full.",
            actions=[
                "Run: du -xh /var | sort -h | tail",
                "Rotate or delete old logs in /var/log/httpd",
                "Extend the EBS volume and grow the filesystem",
            ],
            fix="Enable logrotate for httpd and add a disk-usage alarm at 80%.",
        ),
    ),
    dict(
        key="ec2",
        title="EC2 instance stopped",
        trigger="EventBridge rule aiops-ec2-state-change-dev",
        event=ec2,
        logs="\n".join(
            [
                "[10:29:40Z] INFO  systemd: Stopping httpd.service",
                "[10:29:55Z] INFO  systemd: Reached target Shutdown",
                "[10:30:00Z] ERROR instance i-0abc123def456789 shutdown requested by user ssm-user",
            ]
        ),
        ai=dict(
            severity="MEDIUM",
            confidence="MEDIUM",
            summary="The instance was shut down on request and httpd stopped cleanly.",
            root_cause="Logs show a clean systemd shutdown initiated by ssm-user, so this looks like a manual stop rather than a crash.",
            actions=[
                "Confirm the stop was planned with the change owner",
                "Start it again: aws ec2 start-instances --instance-ids i-0abc123def456789",
                "Check the ASG replaced capacity",
            ],
            fix="Restrict who can stop production instances and tag planned maintenance.",
        ),
    ),
    dict(
        key="db",
        title="Database connection failures",
        trigger="CloudWatch alarm aiops-network-in-high-dev",
        event=cw(
            "aiops-network-in-high-dev", "NetworkIn > 50000000 for 1 datapoint", "InstanceId", "i-0abc123def456789"
        ),
        logs="\n".join(
            [
                "[10:26:00Z] INFO  worker: 480 requests/min",
                "[10:28:10Z] ERROR connection refused to postgres:5432 (10.0.3.7)",
                "[10:28:40Z] ERROR timeout after 30s waiting for db pool",
                "[10:29:20Z] ERROR retry storm: 1200 reconnect attempts, token=abc123secret",
                "[10:30:05Z] WARN  circuit breaker open",
            ]
        ),
        ai=dict(
            severity="HIGH",
            confidence="HIGH",
            summary="The app cannot reach PostgreSQL and is flooding it with reconnect attempts.",
            root_cause="'connection refused to postgres:5432' and 'timeout after 30s' show the database is unreachable; the retry storm explains the network spike.",
            actions=[
                "Check the database instance status and security group on port 5432",
                "Add exponential backoff to the reconnect logic",
                "Restart the DB pool once the database is healthy",
            ],
            fix="Add retry backoff with jitter and a database health alarm.",
        ),
    ),
]


def build():
    out = []
    for s in S:
        inc = parse_event(s["event"])
        inc["raw_logs"] = s["logs"]
        p = process(inc)
        out.append(
            dict(
                key=s["key"],
                title=s["title"],
                trigger=s["trigger"],
                event_type=inc["event_type"],
                alarm=inc["alarm_name"],
                state=inc["new_state"],
                log_group=inc["log_group"],
                raw=s["logs"],
                clean=p["processed_logs"],
                error_type=p["error_type"],
                chars=p["log_char_count"],
                ai=s["ai"],
            )
        )
    tpl_path = os.path.join(ROOT, "dashboard", "template.html")
    out_path = os.path.join(ROOT, "dashboard", "index.html")
    with open(tpl_path, encoding="utf-8") as f:
        html = f.read().replace("__SCEN__", json.dumps(out).replace("</", "<\\/"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)


if __name__ == "__main__":
    path = build()
    print("Dashboard written to", path)
    if "--no-open" not in sys.argv:
        webbrowser.open("file:///" + path.replace("\\", "/").lstrip("/"))
