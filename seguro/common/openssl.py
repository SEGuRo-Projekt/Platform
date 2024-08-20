# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

"""
https://github.com/tpm2-software/tpm2-openssl/blob/master/docs/keys.md

Sign with TPM
   echo -n "hello world" | openssl pkeyutl \
        -provider base \
        -provider tpm2 \
        -inkey testkey.priv \
        -sign \
        -digest sha256 \\k
        -rawin | xxd -p
"""

import os
import shutil
import subprocess
from asn1crypto import pem, x509
from pathlib import Path
from contextlib import contextmanager
from tempfile import TemporaryFile
from typing import IO
import urllib.request
import logging


class Error(RuntimeError):

    def __init__(self, code: int, error: str):
        self.code = code
        self.error = error

    def __str__(self):
        return f"OpenSSL failed: rc={self.code}: {self.error}"


class Certificate:

    def __init__(self, cert: x509.Certificate):
        self.cert = cert

    def public_key(self) -> "PublicKey":
        return PublicKey(
            self.cert.public_key.dump(True),
            self.cert.public_key.algorithm,
        )

    @classmethod
    def read_pem(cls, f: IO):
        typ, hdr, buf = pem.unarmor(f.read())

        if typ == "CERTIFICATE":
            cert = x509.Certificate.load(buf, strict=True)
        else:
            raise Exception("Unsupported PEM type")

        return cls(cert)


class PublicKey:

    def __init__(self, key: bytes, alg: str):
        self.key = key
        self.algorithm = alg


class PrivateKey:

    def __init__(self, key: bytes, alg: str):
        self.key = key
        self.algorithm = alg

    def public_key(self, ssl) -> PublicKey:
        if self.algorithm == "tss2":
            subcmd = "pkey"
        else:
            subcmd = self.algorithm

        proc = ssl._run(
            subcmd,
            # fmt: off
            args=[
                "-inform", "DER",
                "-outform", "DER",
                "-pubout"
            ],
            # fmt: on
            input=self.key,
            capture_output=True,
            check=True,
        )

        return PublicKey(proc.stdout, self.algorithm)

    @classmethod
    def read_pem(cls, f: IO) -> "PrivateKey":
        pem_type, _, buf = pem.unarmor(f.read())

        if pem_type == "PRIVATE KEY":
            algorithm = "rsa"
        elif pem_type == "EC PRIVATE KEY":
            algorithm = "ec"
        elif pem_type == "TSS2 PRIVATE KEY":
            algorithm = "tss2"
        else:
            raise Exception("Unsupported PEM type")

        return cls(buf, algorithm)

    def write_pem(self, f: IO):
        f.write(pem.armor(self.pem_type, self.key))

    @property
    def pem_type(self):
        if self.algorithm == "rsa":
            return "PRIVATE KEY"
        elif self.algorithm == "ec":
            return "EC PRIVATE KEY"
        elif self.algorithm == "tss2":
            return "TSS2 PRIVATE KEY"
        else:
            raise Exception(f"Unsupported key type: {type(self.algorithm)}")


class OpenSSL:

    def __init__(
        self,
        providers: list[str] = ["default"],
        modules_path: Path | None = None,
        bin: Path | None = None,
    ):
        self.logger = logging.getLogger("openssl")
        self.bin = bin
        self.providers = {}  # Maps provider identity -> shared library

        if self.bin is None:
            if env_bin := os.environ.get("OPENSSL_BIN"):
                self.bin = Path(env_bin)
            elif env_shell := shutil.which("openssl"):
                self.bin = Path(env_shell)
            else:
                self.bin = [Path("/usr") / "bin" / "openssl"]

        self.logger.info("Using OpenSSL: %s", self.bin)

        if modules_path is None:
            if (
                env_modules_path := os.environ.get("OPENSSL_MODULES")
            ) is not None:
                modules_path = env_modules_path

        self.logger.info("Using OpenSSL providers:")
        for provider in providers:
            module = Path(provider)
            identity = module.stem

            if identity in ["default", "base", "fips", "legacy"]:
                module = None
            else:
                if not module.is_absolute():
                    module = modules_path / module

                if module.suffix != ".so":
                    module = module.with_suffix(".so")

            self.providers[identity] = module

            self.logger.info(" - %s: %s", identity, module or "null")

        self.logger.debug("OpenSSL config:\n%s", self._config)

    def generate_keypair(
        self,
        alg: str = "rsa",
        rsa_bits: int = 2048,
        ec_group: str = "P-256",
        provider: str = "default",
    ) -> PrivateKey:
        opts = ["-propquery", f"?provider={provider}"]
        if alg == "rsa":
            opts += ["-pkeyopt", f"bits:{rsa_bits}"]
        elif alg == "ec":
            opts += ["-pkeyopt", f"group:{ec_group}"]
        else:
            raise RuntimeError("Unsupported algorithm")

        proc = self._run(
            "genpkey",
            # fmt: off
            args=[
                "-outform", "DER",
                "-algorithm", alg,
            ] + opts,
            # fmt: off
            capture_output=True,
            check=True,
        )

        return PrivateKey(proc.stdout, alg)

    def sign(
        self, sk: PrivateKey, digest: bytes, digest_type: str = "sha256"
    ) -> bytes:
        with TemporaryFile() as kf:
            kf.write(sk.key)
            kf.flush()

            proc = self._run(
                "pkeyutl",
                # fmt: off
                args=[
                    "-sign",
                    "-keyform", "DER",
                    "-inkey", f"/dev/fd/{kf.fileno()}",
                    "-pkeyopt", f"digest:{digest_type}"
                ],
                # fmt: on
                input=digest,
                capture_output=True,
                pass_fds=[kf.fileno()],
            )

            return proc.stdout

    def verify_signature(
        self,
        pk: PublicKey,
        sig: bytes,
        digest: bytes,
        digest_type: str = "sha256",
    ) -> bool:
        with TemporaryFile() as kf, TemporaryFile() as sf:
            kf.write(pk.key)
            kf.flush()

            sf.write(sig)
            sf.flush()

            proc = self._run(
                "pkeyutl",
                # fmt: off
                args=[
                    "-verify",
                    "-pubin",
                    "-keyform", "DER",
                    "-inkey", f"/dev/fd/{kf.fileno()}",
                    "-sigfile", f"/dev/fd/{sf.fileno()}",
                    "-pkeyopt", f"digest:{digest_type}",
                ],
                # fmt: on
                input=digest,
                capture_output=True,
                check=True,
                pass_fds=[kf.fileno(), sf.fileno()],
            )

        return proc.stdout

    def timestamp_query(self, url: str, digest: bytes):
        proc = self._run(
            "ts",
            args=["-query", "-digest", digest.hex(), "-no_nonce"],
            capture_output=True,
            check=True,
        )

        req = urllib.request.Request(
            url,
            data=proc.stdout,
            headers={"Content-Type": "application/timestamp-query"},
        )

        with urllib.request.urlopen(req) as resp:
            return resp.read()

    def timestamp_verify(
        self,
        tsr: bytes,
        digest: bytes,
        ca_file: str,
        untrusteds: list[str] = [],
    ):
        # openssl ts -verify -digest b7e5d3f93198b38379852f2c04e78d73abdd0f4b -in design2.tsr -CAfile cacert.pem

        verify_args = []
        if ca_file is not None:
            verify_args += ["-CAfile", ca_file]

            for untrusted in untrusteds:
                verify_args += ["-untrusted", untrusted]

        proc = self._run(
            "ts",
            args=[
                "-verify",
                "-digest",
                digest.hex(),
                "-in",
                "/dev/stdin",
            ]
            + verify_args,
            input=tsr,
            capture_output=True,
            check=True,
        )

        return proc.stdout

    @property
    def _config(self):
        return f"""openssl_conf = openssl_init

[openssl_init]
providers = providers

[providers]
{'\n'.join([f'{p} = {p}_provider' for p in self.providers])}

{'\n\n'.join([(f'''[{p}_provider]
activate = 1''' + (f'''
module = {m}''' if m is not None else '')) for p, m in self.providers.items()])}
"""

    @contextmanager
    def _config_file(self):
        with TemporaryFile("w+t") as f:
            f.write(self._config)
            f.flush()

            yield f

    def _run(self, subcmd, **kwargs):
        with self._config_file() as cf:
            if cf is not None:
                env = kwargs.setdefault("env", {})
                env.update({"OPENSSL_CONF": f"/dev/fd/{cf.fileno()}"})

                pass_fds = kwargs.setdefault("pass_fds", [])
                pass_fds.append(cf.fileno())

            args = kwargs.pop("args", [])
            args = (
                # fmt: off
                [
                    self.bin,
                    subcmd,
                ]
                # fmt: on
                + args
            )

            self.logger.debug("Running: %s", args)

            try:
                return subprocess.run(args, **kwargs)
            except subprocess.CalledProcessError as e:
                raise Error(e.returncode, e.stderr)
