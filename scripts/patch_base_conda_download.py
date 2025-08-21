# scripts/patch_base_conda_download.py
import os, re, shutil, pathlib
import swebench.harness.docker_build as db

_ORIG_BUILD_IMAGE = db.build_image

# --------------------- base image hardening (conda fetch) ---------------------
def _harden_conda_fetch(dockerfile: str) -> str:
    pat = (
        r"RUN\s+wget\s+'https://repo\.anaconda\.com/miniconda/Miniconda3-[^']+Linux-x86_64\.sh'"
        r"\s+-O\s+miniconda\.sh\s+&&\s+bash\s+miniconda\.sh\s+-b\s+-p\s+/opt/miniconda3"
    )
    url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
    rep = (
        "RUN curl -L --retry 5 -o miniconda.sh '{url}' && "
        "bash miniconda.sh -b -p /opt/miniconda3"
    ).format(url=url)
    new_df, n = re.subn(pat, rep, dockerfile, count=1)
    if n:
        print("[patch_base_conda_download] Conda fetch replacement applied: 1 change(s)")
    return new_df

def _inject_ca_bundle(dockerfile: str, build_dir: str) -> str:
    """
    Copy the org CA into the build context and inject it into the Dockerfile
    *after* the apt install block, guaranteeing update-ca-certificates exists.
    """
    import os, shutil, re, pathlib
    ca = os.environ.get("SWE_EXTRA_CA_CERT_FILE")
    if not ca or not os.path.isfile(ca):
        return dockerfile

    ctx_ca = pathlib.Path(build_dir) / "custom-ca.crt"
    try:
        shutil.copyfile(ca, ctx_ca)
    except Exception:
        return dockerfile

    # apt install block (multi-line, ends with 'rm -rf /var/lib/apt/lists/*')
    apt_block = re.compile(
        r"(RUN\s+apt\s+update\s+&&\s+apt\s+install\s+-y[\s\S]*?rm\s+-rf\s+/var/lib/apt/lists/\*)",
        re.IGNORECASE,
    )
    # Inject CA right after the apt block, ensuring ca-certificates is present.
    inject = (
        "\nADD custom-ca.crt /usr/local/share/ca-certificates/custom-ca.crt\n"
        "RUN apt-get update && apt-get install -y ca-certificates && "
        "update-ca-certificates && rm -rf /var/lib/apt/lists/*\n"
    )

    m = apt_block.search(dockerfile)
    if m:
        start, end = m.span()
        dockerfile = dockerfile[:end] + "\n" + inject + dockerfile[end:]
    else:
        # Fallback: inject right after FROM if we can't find the apt block
        dockerfile = re.sub(
            r"^(FROM[^\n]+\n)",
            r"\1" + inject,
            dockerfile,
            count=1,
            flags=re.MULTILINE,
        )

    print("[patch_base_conda_download] Injected extra CA from SWE_EXTRA_CA_CERT_FILE (post-apt).")
    return dockerfile

# --------------------- env image hardening (SSL everywhere) -------------------
def _harden_env_dockerfile(dockerfile: str, insecure: bool = False, extra_ca_path: str = None, **_ignored):
    """
    - Ensure CA env vars are set
    - Configure conda/pip/git to use system CA
    - Rewrite setup_env.sh to install pytest via conda (fallback to pip with bigger timeouts)
    """
    import re

    # 1) Add CA env vars if missing
    if "REQUESTS_CA_BUNDLE" not in dockerfile:
        dockerfile = dockerfile.replace(
            "FROM --platform=linux/x86_64 sweb.base.py.x86_64:latest",
            "FROM --platform=linux/x86_64 sweb.base.py.x86_64:latest\n"
            "ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt "
            "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt "
            "CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt "
            "PIP_DEFAULT_TIMEOUT=180 PIP_NO_CACHE_DIR=1",
            1,
        )

    # 3) Prefer conda for pytest; fallback to pip with longer timeouts/retries
    dockerfile = dockerfile.replace(
        "RUN sed -i -e 's/\\r$//' /root/setup_env.sh",
        "RUN sed -i -e 's/\\r$//' /root/setup_env.sh\n"
        "RUN sed -i 's#python -m pip install pytest#conda install -n testbed -y -c conda-forge pytest || python -m pip install --timeout 180 --retries 8 --no-cache-dir pytest#' /root/setup_env.sh",
        1,
    )

    print("[patch_base_conda_download] Env Dockerfile hardened (conda-first pytest + pip fallback).")
    return dockerfile



def _patched_build_image(*args, **kwargs):
    # Extract call params whether positional or kwargs
    image_name = kwargs.get("image_name")
    dockerfile = kwargs.get("dockerfile")
    build_dir  = kwargs.get("build_dir")

    if image_name is None and len(args) >= 2:
        image_name = args[1]
    if dockerfile is None and len(args) >= 3:
        dockerfile = args[2]
    if build_dir is None and len(args) >= 6:
        build_dir = args[5]

    insecure = os.environ.get("SWE_SSL_INSECURE") == "1"

    if isinstance(dockerfile, str):
        name = str(image_name) if image_name is not None else ""

        # base image: swap Miniconda wget for Miniforge curl + add CA if provided
        if name.startswith("sweb.base.py.x86_64:"):
            df = _harden_conda_fetch(dockerfile)
            df = _inject_ca_bundle(df, build_dir or ".")
            if "dockerfile" in kwargs: kwargs["dockerfile"] = df
            else: args = list(args); args[2] = df; args = tuple(args)

        # env image: make CA trusted by conda/pip/git before setup_env.sh
        elif name.startswith("sweb.env.py.x86_64.") or "/root/setup_env.sh" in dockerfile:
            df = _harden_env_dockerfile(dockerfile, insecure=insecure)
            if "dockerfile" in kwargs: kwargs["dockerfile"] = df
            else: args = list(args); args[2] = df; args = tuple(args)

    return _ORIG_BUILD_IMAGE(*args, **kwargs)

db.build_image = _patched_build_image

if os.environ.get("SWE_SSL_INSECURE") == "1":
    print("[patch_base_conda_download] Enabled (CA injection + Miniforge curl).")
else:
    print("[patch_base_conda_download] Hardened Miniconda download step.")

