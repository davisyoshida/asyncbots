from setuptools import setup

with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='asyncbots',
    version='0.1.1',
    packages=['asyncbots'],
    license='MIT',
    long_description=long_description,
    description='A framework for Slack RTM bots.',
    url='https://github.com/davisyoshida/asyncbots',
    author='Davis Yoshida',
    author_email='dyoshida@ttic.edu',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires=['mongoengine', 'pyparsing', 'requests', 'websockets'],
    keywords='slack chatbot rtm bot',
    python_requires='>=3.5'
)
