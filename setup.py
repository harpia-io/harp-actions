from setuptools import setup, find_packages


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

tests_require = [],

setup(
    name='harp-actions',
    version='0.1',
    description='Actions service',
    url='',
    author='',
    author_email='',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Programming Language :: Python :: 3.9',
    ],
    keywords=[],
    packages=find_packages(),
    install_requires=requirements,
    tests_require=tests_require,
    entry_points={
        'console_scripts': ['harp-actions = actions.app:main']
    },
    zip_safe=False,
    cmdclass={}
)
