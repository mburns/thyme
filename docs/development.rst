Development Guide
================

Setting Up Development Environment
---------------------------------

1. Clone the repository and install dependencies (see :doc:`installation`)
2. Install development tools:

   .. code-block:: bash

      pip install black flake8 isort mypy pytest pytest-cov sphinx sphinx-rtd-theme

Development Commands
-------------------

The project includes a Makefile with common development commands:

.. code-block:: bash

   # Run the application
   make run

   # Lint the code
   make lint

   # Format the code
   make format

   # Run tests
   make test

   # Generate documentation
   make docs

Type Checking
------------

The project uses mypy for static type checking. Run type checking with:

.. code-block:: bash

   mypy thyme sample_data.py

Code Style
----------

The project uses:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting

Run all style checks with:

.. code-block:: bash

   make format
   make lint

Testing
-------

Run tests with coverage:

.. code-block:: bash

   pytest --cov=thyme --cov-report=html

This will generate an HTML coverage report in the `htmlcov/` directory.

Documentation
-------------

Generate documentation:

.. code-block:: bash

   cd docs
   make html

The documentation will be generated in `docs/_build/html/`.

Project Structure
----------------

::

   thyme/
   ├── thyme/                 # Main application package
   │   ├── __init__.py       # Flask app and models
   │   └── __main__.py       # Entry point
   ├── templates/            # HTML templates
   ├── static/              # CSS, JS, images
   ├── docs/                # Documentation
   ├── tests/               # Test files
   ├── requirements.txt     # Dependencies
   ├── pyproject.toml       # Build configuration
   ├── setup.cfg           # Package configuration
   ├── Makefile            # Development commands
   ├── Dockerfile          # Container configuration
   └── sample_data.py      # Sample data script

Database Schema
--------------

The Event model includes the following fields:

- ``id``: Primary key (Integer)
- ``title``: Event title (String, required)
- ``description``: Event description (Text, optional)
- ``start_date``: Start date (DateTime, required)
- ``end_date``: End date (DateTime, optional)
- ``media_url``: Media URL (String, optional)
- ``media_caption``: Media caption (String, optional)
- ``media_credit``: Media credit (String, optional)
- ``group``: Event group (String, optional)
- ``background_color``: Background color (String, optional)
- ``text_color``: Text color (String, optional)

Contributing
-----------

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run linting and tests: ``make lint && make test``
6. Submit a pull request 