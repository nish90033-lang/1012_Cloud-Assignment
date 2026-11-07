"""Host-side helper for the object store (SeaweedFS S3 on http://localhost:8333).

  s3tool.py mkbuckets
  s3tool.py put BUCKET KEY FILE            s3tool.py get BUCKET KEY FILE
  s3tool.py put-dir BUCKET PREFIX DIR      (uploads every file in DIR under PREFIX/)
  s3tool.py publish-model VERSION [--release-url URL]   (artifacts/VERSION or a GitHub Release asset -> models/VERSION/)
Credentials: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from the environment (.secrets/s3.env via the Makefile).
"""
import argparse
import hashlib
import os
import sys
import tarfile
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))
import s3util  # noqa: E402

ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:8333")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def put_dir(s3, bucket, prefix, d):
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            s3.upload_file(p, bucket, f"{prefix}/{name}")
            print(f"  uploaded {bucket}/{prefix}/{name}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mkbuckets")
    for n in ("put", "get"):
        p = sub.add_parser(n)
        p.add_argument("bucket")
        p.add_argument("key")
        p.add_argument("file")
    p = sub.add_parser("put-dir")
    p.add_argument("bucket")
    p.add_argument("prefix")
    p.add_argument("dir")
    p = sub.add_parser("publish-model")
    p.add_argument("version")
    p.add_argument("--release-url")
    a = ap.parse_args()
    s3 = s3util.client(ENDPOINT)

    if a.cmd == "mkbuckets":
        for attempt in range(30):  # SeaweedFS may need a few seconds after the Pod is Ready
            try:
                existing = {b["Name"] for b in s3.list_buckets()["Buckets"]}
                for b in ("datasets", "models"):
                    if b not in existing:
                        s3.create_bucket(Bucket=b)
                print("buckets:", sorted({b["Name"] for b in s3.list_buckets()["Buckets"]}))
                return
            except Exception as exc:
                print(f"waiting for object store ({exc.__class__.__name__})")
                time.sleep(4)
        sys.exit("object store not reachable")
    if a.cmd == "put":
        s3.upload_file(a.file, a.bucket, a.key)
    elif a.cmd == "get":
        s3.download_file(a.bucket, a.key, a.file)
    elif a.cmd == "put-dir":
        put_dir(s3, a.bucket, a.prefix.strip("/"), a.dir)
    elif a.cmd == "publish-model":
        v = a.version
        if a.release_url:  # fresh clone: take the model from the GitHub Release
            tmp = tempfile.mkdtemp()
            tgz = os.path.join(tmp, f"model-{v}.tar.gz")
            urllib.request.urlretrieve(a.release_url, tgz)
            urllib.request.urlretrieve(a.release_url.rsplit("/", 1)[0] + "/model.sha256", os.path.join(tmp, "model.sha256"))
            want = open(os.path.join(tmp, "model.sha256")).read().split()[0]
            if sha256(tgz) != want:
                sys.exit("checksum mismatch for the release asset")
            d = os.path.join(tmp, v)
            os.makedirs(d)
            with tarfile.open(tgz) as t:
                t.extractall(d, filter="data")
            open(os.path.join(d, "model.sha256"), "w").write(open(os.path.join(tmp, "model.sha256")).read())
        else:
            d = os.path.join("artifacts", v)
        put_dir(s3, "models", f"{v}", d)


if __name__ == "__main__":
    main()
