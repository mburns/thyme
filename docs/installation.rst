Installation
============

Prerequisites
------------

- Python 3.8 or higher
- pip

Installation Steps
-----------------

1. **Clone the repository**:
   .. code-block:: bash

      git clone <repository-url>
      cd thyme

2. **Create a virtual environment**:
   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**:
   .. code-block:: bash

      pip install -r requirements.txt

4. **Run the application**:
   .. code-block:: bash

      python -m thyme

5. **Open your browser** and navigate to:
   - Timeline view: http://localhost:5000
   - Admin interface: http://localhost:5000/admin

Docker Installation
------------------

1. **Build the Docker image**:
   .. code-block:: bash

      docker build -t thyme-app .

2. **Run the container**:
   .. code-block:: bash

      docker run -p 5000:5000 thyme-app

Development Installation
------------------------

For development, install additional tools:

.. code-block:: bash

   pip install -r requirements.txt
   pip install black flake8 isort mypy pytest pytest-cov sphinx sphinx-rtd-theme 