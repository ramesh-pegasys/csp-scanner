from app.cloud.base import CloudProvider


def test_cloud_provider_enum_members():
    values = [provider.value for provider in CloudProvider]
    assert values == ["aws", "azure", "gcp"]
    assert CloudProvider("aws") is CloudProvider.AWS
