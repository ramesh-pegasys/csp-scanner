"""Tests for ExtractorRegistry."""

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.extractors.base import BaseExtractor, ExtractorMetadata
from app.services.registry import ExtractorRegistry


class DummyExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="dummy",
            version="1.0",
            description="Dummy extractor",
            resource_types=["dummy"],
        )

    async def extract(self, region=None, filters=None):
        return [{"resource_id": "dummy"}]

    def transform(self, raw_data):
        return {
            "resource_id": "dummy",
            "resource_type": "dummy",
            "service": "dummy",
            "configuration": {},
        }


@pytest.fixture
def registry(tmp_path):
    session = SimpleNamespace()
    settings = Settings()
    with patch.object(
        ExtractorRegistry, "_register_default_extractors", lambda self: None
    ):
        reg = ExtractorRegistry(session, settings)
    extractor_config = tmp_path / "extractors.yaml"
    extractor_config.write_text("dummy:\n  option: value\n")
    reg.config.extractor_config_path = str(extractor_config)
    return reg


def test_register_and_retrieve_extractor(registry):
    registry.register(DummyExtractor)

    extractor = registry.get("dummy")
    assert extractor is not None
    assert extractor.metadata.service_name == "dummy"

    all_services = registry.list_services()
    assert "dummy" in all_services

    multiple = registry.get_extractors(["dummy"])
    assert len(multiple) == 1


def test_register_invalid_extractor(caplog, registry):
    class ExplodingExtractor(DummyExtractor):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name="exploding",
                version="1.0",
                description="Exploding extractor",
                resource_types=["boom"],
            )

    with caplog.at_level("ERROR"):
        registry.register(ExplodingExtractor)
    assert any("Failed to register" in message for message in caplog.messages)


def make_dummy_extractor(service_name):
    class _Extractor(DummyExtractor):
        def get_metadata(self) -> ExtractorMetadata:
            return ExtractorMetadata(
                service_name=service_name,
                version="1.0",
                description=f"{service_name} extractor",
                resource_types=[service_name],
            )

    return _Extractor


def test_register_default_extractors(monkeypatch, registry):
    modules = {
        "app.extractors.ec2": SimpleNamespace(EC2Extractor=make_dummy_extractor("ec2")),
        "app.extractors.s3": SimpleNamespace(S3Extractor=make_dummy_extractor("s3")),
        "app.extractors.rds": SimpleNamespace(RDSExtractor=make_dummy_extractor("rds")),
        "app.extractors.lambda_extractor": SimpleNamespace(
            LambdaExtractor=make_dummy_extractor("lambda")
        ),
        "app.extractors.iam": SimpleNamespace(IAMExtractor=make_dummy_extractor("iam")),
        "app.extractors.vpc": SimpleNamespace(VPCExtractor=make_dummy_extractor("vpc")),
        "app.extractors.apprunner": SimpleNamespace(
            AppRunnerExtractor=make_dummy_extractor("apprunner")
        ),
        "app.extractors.ecs": SimpleNamespace(ECSExtractor=make_dummy_extractor("ecs")),
        "app.extractors.eks": SimpleNamespace(EKSExtractor=make_dummy_extractor("eks")),
        "app.extractors.elb": SimpleNamespace(ELBExtractor=make_dummy_extractor("elb")),
        "app.extractors.cloudfront": SimpleNamespace(
            CloudFrontExtractor=make_dummy_extractor("cloudfront")
        ),
        "app.extractors.apigateway": SimpleNamespace(
            APIGatewayExtractor=make_dummy_extractor("apigateway")
        ),
        "app.extractors.kms": SimpleNamespace(KMSExtractor=make_dummy_extractor("kms")),
    }

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    registry._register_default_extractors()
    services = registry.list_services()

    expected_services = [
        "ec2",
        "s3",
        "rds",
        "lambda",
        "iam",
        "vpc",
        "apprunner",
        "ecs",
        "eks",
        "elb",
        "cloudfront",
        "apigateway",
        "kms",
    ]
    for service_name in expected_services:
        assert service_name in services

    assert len(registry.get_extractors()) == len(services)
