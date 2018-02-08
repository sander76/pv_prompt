from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()



setup(
    name='pv_prompt',
    long_description=readme(),
    version='1.0',
    packages=['pv_prompt'],
    url='https://github.com/sander76/pv_prompt',
    license='Apache License 2.0',
    author='Sander Teunissen',
    classifiers=[
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    description='PowerView shades toolkit',
    install_requires=["aiopvapi", "prompt-toolkit==2.0.0", "pysmb"],
    entry_points={
        'console_scripts': ['pv_prompt=pv_prompt.async_prompt:main']
    }
)
