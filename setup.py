from distutils.core import setup

setup(
    name='DupTool',
    version='0.1.0',
    author='Michal Koperski',
    author_email='m.koperski@gmail.com',
    packages=['duptool_glacier_cli', 'duptool'],
    scripts=['bin/duptool_notification.py', 'bin/duptool'],
    url='http://pypi.python.org/pypi/DupTool/',
    license='LICENSE.txt',
    description='Duplicity backup wrapper.',
    long_description=open('README.txt').read(),
    install_requires=[
    ],
)
