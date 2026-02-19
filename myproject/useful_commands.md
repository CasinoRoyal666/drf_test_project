# API Versioning Tests URLS

`http://localhost:8000/api/passports/?version=2&checker_role=customs`
`http://localhost:8000/api/passports/?version=1&checker_role=customs`
`http://localhost:8000/api/passports/2/?version=2&checker_role=customs`

# Coverage Tests:

from .. folder
-----
To run
`coverage run --source='.' manage.py test` 
To report
`coverage report`
-----

# pytest + coverage + xdist

from ..folder
-----
To run
`pytest -n auto --cov=core --cov-report=html --cov-report=term`



