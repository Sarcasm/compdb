compdb: the compilation database Swiss army knife
=================================================

.. contents:: :local:


Introduction
------------

compdb_ is a command line tool to manipulates compilation databases.
A compilation database is a database for compile options,
it has records of which compile options are used to build the files in a project.
An example of compilation database is the `JSON Compilation Database`_

``compdb`` aims to make it easier for you to run tools on your codebase
by spoon-feeding you the right compile options.

``compdb`` is not so much about generating the initial compilation database,
this, is left to other tools, such as ``cmake`` and ``ninja``.
It is only a glue between the initial compilation database and your tool(s).


Motivation
----------

With the proliferation of Clang-based tools,
it has become apparent that the compile options
are no longer useful uniquely to the compiler.

Standalone tools such as clang-tidy_
or text editors with libclang_ integration have to deal with compile options.

Examples of such tools, dealing with compilation databases are:
irony-mode_, rtags_ and ycmd_.

Based on this evidence, ``compdb`` came to life.
A tool that has knowledge of the compile options and can share it
both to inform the text editor and to run clang based tool from the shell.


Getting started
---------------

Installation
~~~~~~~~~~~~

Install with pip_::

  pip install compdb

From Github, as user::

  pip install --user git+https://github.com/Sarcasm/compdb.git#egg=compdb


Generate a compilation database with header files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming a build directory ``build/``, containing a ``compile_commands.json``,
a new compilation database, containing the header files,
can be generated with::

  compdb -p build/ list > compile_commands.json


Running the tests
~~~~~~~~~~~~~~~~~

To run the tests, type::

  python -m tests

Or::

  tox --skip-missing-interpreters

For regression tests on a few open source projects::

  cd tests/regression/headerdb
  make [all|help]


Contribute
----------

Contributions are always welcome!

Try to be consistent with the actual code, it will ease the review.


License
-------

This project is licensed under the MIT License.
See LICENSE.txt for details.


Acknowledgments
---------------

* repo_: for its ubiquitous command line interface,
  which served as an inspiration
* scan-build_: for the clear Python package design
* git_: for the ``git-config`` API
* `julio.meroh.net`_: for the interesting article serie on `CLI design`_


.. _clang-tidy: http://clang.llvm.org/extra/clang-tidy/
.. _CLI design: https://julio.meroh.net/2013/09/cli-design-series-wrap-up.html
.. _compdb: https://github.com/Sarcasm/compdb
.. _git: https://git-scm.com/
.. _irony-mode: https://github.com/Sarcasm/irony-mode
.. _julio.meroh.net: https://julio.meroh.net/
.. _JSON Compilation Database: http://clang.llvm.org/docs/JSONCompilationDatabase.html
.. _libclang: http://clang.llvm.org/doxygen/group__CINDEX.html
.. _pip: https://pip.pypa.io/
.. _repo: https://gerrit.googlesource.com/git-repo/
.. _rtags: https://github.com/Andersbakken/rtags
.. _scan-build: https://github.com/rizsotto/scan-build
.. _ycmd: https://github.com/Valloric/ycmd
