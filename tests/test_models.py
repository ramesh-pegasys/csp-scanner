"""Tests for models"""

from datetime import datetime
from unittest.mock import Mock, patch
from app.models.job import Job, JobStatus
from app.models.artifact import CloudArtifact
from app.models.database import (
    DatabaseManager,
    ConfigEntry,
    get_db_manager,
    init_database,
)


def test_job_model():
    """Test Job model creation and validation"""
    job = Job(
        id="test-job-123",
        status=JobStatus.RUNNING,
        started_at=datetime(2023, 1, 1, 12, 0, 0),
        services=["s3", "ec2"],
        total_artifacts=10,
        successful_artifacts=8,
        failed_artifacts=2,
        errors=["Error 1", "Error 2"],
    )

    assert job.id == "test-job-123"
    assert job.status == JobStatus.RUNNING
    assert job.started_at == datetime(2023, 1, 1, 12, 0, 0)
    assert job.services == ["s3", "ec2"]
    assert job.total_artifacts == 10
    assert job.successful_artifacts == 8
    assert job.failed_artifacts == 2
    assert job.errors == ["Error 1", "Error 2"]
    assert job.completed_at is None


def test_job_model_defaults():
    """Test Job model with default values"""
    job = Job(
        id="test-job-456",
        status=JobStatus.PENDING,
        started_at=datetime(2023, 1, 1, 12, 0, 0),
        services=["s3"],
    )

    assert job.total_artifacts == 0
    assert job.successful_artifacts == 0
    assert job.failed_artifacts == 0
    assert job.errors == []


def test_job_status_enum():
    """Test JobStatus enum values"""
    assert JobStatus.PENDING == "pending"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"


def test_cloud_artifact_model():
    """Test CloudArtifact model"""
    artifact = CloudArtifact(
        resource_id="my-bucket",
        resource_type="bucket",
        service="s3",
        region="us-east-1",
        account_id="123456789012",
        configuration={"name": "my-bucket", "created": "2023-01-01"},
        raw={"raw_data": "value"},
        extracted_at=datetime(2023, 1, 1, 12, 0, 0),
    )

    assert artifact.resource_id == "my-bucket"
    assert artifact.resource_type == "bucket"
    assert artifact.service == "s3"
    assert artifact.region == "us-east-1"
    assert artifact.account_id == "123456789012"
    assert artifact.configuration == {"name": "my-bucket", "created": "2023-01-01"}
    assert artifact.raw == {"raw_data": "value"}
    assert artifact.extracted_at == datetime(2023, 1, 1, 12, 0, 0)


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_init(mock_sessionmaker, mock_create_engine):
    """Test DatabaseManager initialization"""
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine
    mock_session = Mock()
    mock_sessionmaker.return_value = mock_session

    db_manager = DatabaseManager("postgresql://test")

    mock_create_engine.assert_called_once_with("postgresql://test", echo=False)
    mock_sessionmaker.assert_called_once_with(
        autocommit=False, autoflush=False, bind=mock_engine
    )
    assert db_manager.engine == mock_engine
    assert db_manager.SessionLocal == mock_session


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
@patch.dict("os.environ", {}, clear=True)
def test_database_manager_init_default_url(mock_sessionmaker, mock_create_engine):
    """Test DatabaseManager initialization with default URL"""
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine
    mock_session = Mock()
    mock_sessionmaker.return_value = mock_session

    db_manager = DatabaseManager()

    mock_create_engine.assert_called_once_with(
        "postgresql://localhost/csp_scanner", echo=False
    )
    assert db_manager.engine == mock_engine
    mock_sessionmaker.assert_called_once_with(
        autocommit=False, autoflush=False, bind=mock_engine
    )


@patch("app.models.database.Base")
@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_ensure_tables_exist(
    mock_sessionmaker, mock_create_engine, mock_base
):
    """Test _ensure_tables_exist method"""
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine

    db_manager = DatabaseManager("postgresql://test")

    # Reset call count from __init__
    mock_base.metadata.create_all.reset_mock()

    # This should call create_all
    db_manager._ensure_tables_exist()
    mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_ensure_tables_exist_exception(
    mock_sessionmaker, mock_create_engine
):
    """Test _ensure_tables_exist handles exceptions"""
    mock_engine = Mock()
    # Mock the create_all to raise exception
    import app.models.database

    app.models.database.Base.metadata.create_all = Mock(
        side_effect=Exception("DB error")
    )
    mock_create_engine.return_value = mock_engine

    db_manager = DatabaseManager("postgresql://test")

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        db_manager._ensure_tables_exist()
        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_called_once()


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_is_database_available(mock_sessionmaker, mock_create_engine):
    """Test is_database_available method"""
    mock_engine = Mock()
    mock_conn = Mock()
    mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
    mock_create_engine.return_value = mock_engine

    db_manager = DatabaseManager("postgresql://test")

    result = db_manager.is_database_available()
    assert result is True
    mock_conn.execute.assert_called_once()


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_is_database_available_exception(
    mock_sessionmaker, mock_create_engine
):
    """Test is_database_available handles exceptions"""
    mock_engine = Mock()
    mock_engine.connect.side_effect = Exception("Connection failed")
    mock_create_engine.return_value = mock_engine

    db_manager = DatabaseManager("postgresql://test")

    result = db_manager.is_database_available()
    assert result is False


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_create_tables(mock_sessionmaker, mock_create_engine):
    """Test create_tables method"""
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine

    db_manager = DatabaseManager("postgresql://test")
    with patch("app.models.database.Base.metadata.create_all") as mock_create_all:
        db_manager.create_tables()
        mock_create_all.assert_called_once_with(bind=mock_engine)


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_get_session(mock_sessionmaker, mock_create_engine):
    """Test get_session method"""
    mock_session_instance = Mock()
    mock_sessionmaker.return_value = Mock(return_value=mock_session_instance)

    db_manager = DatabaseManager("postgresql://test")
    session = db_manager.get_session()

    assert session == mock_session_instance


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_get_config_value(mock_sessionmaker, mock_create_engine):
    """Test get_config_value method"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(db_manager, "get_global_config", return_value={"key1": "value1"}):
        result = db_manager.get_config_value("key1")
        assert result == "value1"

        result = db_manager.get_config_value("nonexistent")
        assert result is None


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_get_config_value_no_global(
    mock_sessionmaker, mock_create_engine
):
    """Test get_config_value when no global config exists"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(db_manager, "get_global_config", return_value=None):
        result = db_manager.get_config_value("key1")
        assert result is None


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_set_config_value(mock_sessionmaker, mock_create_engine):
    """Test set_config_value method"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(
        db_manager, "get_global_config", return_value={"existing": "value"}
    ):
        with patch.object(db_manager, "set_global_config") as mock_set_global:
            db_manager.set_config_value("new_key", {"data": "value"}, "description")

            expected_config = {"existing": "value", "new_key": {"data": "value"}}
            mock_set_global.assert_called_once_with(expected_config)


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_set_config_value_no_global(
    mock_sessionmaker, mock_create_engine
):
    """Test set_config_value when no global config exists"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(db_manager, "get_global_config", return_value=None):
        with patch.object(db_manager, "set_global_config") as mock_set_global:
            db_manager.set_config_value("key1", {"data": "value"})

            expected_config = {"key1": {"data": "value"}}
            mock_set_global.assert_called_once_with(expected_config)


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_delete_config_value(mock_sessionmaker, mock_create_engine):
    """Test delete_config_value method"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(
        db_manager,
        "get_global_config",
        return_value={"key1": "value1", "key2": "value2"},
    ):
        with patch.object(db_manager, "set_global_config") as mock_set_global:
            result = db_manager.delete_config_value("key1")

            assert result is True
            expected_config = {"key2": "value2"}
            mock_set_global.assert_called_once_with(expected_config)


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_delete_config_value_not_found(
    mock_sessionmaker, mock_create_engine
):
    """Test delete_config_value when key doesn't exist"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(db_manager, "get_global_config", return_value={"key1": "value1"}):
        with patch.object(db_manager, "set_global_config") as mock_set_global:
            result = db_manager.delete_config_value("nonexistent")

            assert result is False
            mock_set_global.assert_not_called()


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_get_all_config(mock_sessionmaker, mock_create_engine):
    """Test get_all_config method"""
    db_manager = DatabaseManager("postgresql://test")

    with patch.object(db_manager, "get_global_config", return_value={"key1": "value1"}):
        result = db_manager.get_all_config()
        assert result == {"key1": "value1"}

    with patch.object(db_manager, "get_global_config", return_value=None):
        result = db_manager.get_all_config()
        assert result == {}


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_get_global_config(mock_sessionmaker, mock_create_engine):
    """Test get_global_config method"""
    db_manager = DatabaseManager("postgresql://test")
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    db_manager.SessionLocal = Mock(return_value=mock_session)

    mock_entry = Mock()
    mock_entry.value = {"config": "data"}
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = mock_entry
    mock_session.query.return_value = mock_query

    result = db_manager.get_global_config()
    assert result == {"config": "data"}


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_get_global_config_no_entry(
    mock_sessionmaker, mock_create_engine
):
    """Test get_global_config when no entry exists"""
    db_manager = DatabaseManager("postgresql://test")
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    db_manager.SessionLocal = Mock(return_value=mock_session)

    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_query

    result = db_manager.get_global_config()
    assert result is None


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_set_global_config_update(
    mock_sessionmaker, mock_create_engine
):
    """Test set_global_config updating existing entry"""
    db_manager = DatabaseManager("postgresql://test")
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    db_manager.SessionLocal = Mock(return_value=mock_session)

    mock_entry = Mock()
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = mock_entry
    mock_session.query.return_value = mock_query

    config = {"new": "config"}
    db_manager.set_global_config(config)

    assert mock_entry.value == config
    mock_session.commit.assert_called_once()


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_set_global_config_create(
    mock_sessionmaker, mock_create_engine
):
    """Test set_global_config creating new entry"""
    db_manager = DatabaseManager("postgresql://test")
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    db_manager.SessionLocal = Mock(return_value=mock_session)

    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_query

    config = {"new": "config"}
    db_manager.set_global_config(config)

    # Check that ConfigEntry was created and added
    assert mock_session.add.called
    args = mock_session.add.call_args[0]
    entry = args[0]
    assert isinstance(entry, ConfigEntry)
    assert entry.key == "global_config"
    assert entry.value == config
    assert entry.description == "Global application configuration"
    mock_session.commit.assert_called_once()


@patch("app.models.database.create_engine")
@patch("app.models.database.sessionmaker")
def test_database_manager_close(mock_sessionmaker, mock_create_engine):
    """Test close method"""
    mock_engine = Mock()
    mock_create_engine.return_value = mock_engine

    db_manager = DatabaseManager("postgresql://test")
    db_manager.close()

    mock_engine.dispose.assert_called_once()


@patch("app.models.database.DatabaseManager")
def test_get_db_manager(mock_db_manager_class):
    """Test get_db_manager function"""
    # Reset global state
    import app.models.database

    app.models.database._db_manager = None

    mock_instance = Mock()
    mock_db_manager_class.return_value = mock_instance

    result1 = get_db_manager()
    result2 = get_db_manager()

    assert result1 is mock_instance
    assert result2 is mock_instance
    mock_db_manager_class.assert_called_once()


@patch("app.models.database.DatabaseManager")
def test_init_database(mock_db_manager_class):
    """Test init_database function"""
    mock_instance = Mock()
    mock_db_manager_class.return_value = mock_instance

    init_database("postgresql://custom")

    mock_db_manager_class.assert_called_once_with("postgresql://custom")
    mock_instance.create_tables.assert_called_once()
