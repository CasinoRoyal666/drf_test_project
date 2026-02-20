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
Full cov + rep:
`coverage run --source='core' manage.py test core && coverage report -m`
-----

# xdist

from ..folder
-----
To run
`python manage.py test core --parallel auto`



