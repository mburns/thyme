import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import():
    """Test that the thyme module can be imported"""
    try:
        import thyme

        assert hasattr(thyme, "app")
        assert hasattr(thyme, "Event")
        assert hasattr(thyme, "db")
    except ImportError as e:
        # If import fails, provide helpful error message
        raise ImportError(
            f"Could not import thyme module: {e}. Make sure you're running from the project root."
        ) from e


def test_app_creation():
    """Test that the Flask app is created correctly"""
    import thyme

    assert thyme.app is not None
    assert thyme.app.name == "thyme"
