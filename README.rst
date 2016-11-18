compdb: the compilation database Swiss army knife
=================================================

compdb_ is a command line tool to manipulates compilation databases.
A compilation database is a database for compile options,
it has records of which compile options are used to build the files in a project.
An example of compilation database is the `JSON Compilation Database`_

``compdb`` aims to make it easier for you to run tools on your codebase
by spoon-feeding you the right compile options.

``compdb`` is not so much about generating the initial compilation database,
this, is left to other tools, such as ``cmake`` and ``ninja``.
It is only a glue between the initial compilation database and your tool.


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

(TODO) Install with pip_::

  pip install compdb

From Github::

  pip install git+https://github.com/Sarcasm/compdb.git#egg=compdb

From Github, as user::

  pip install --user git+https://github.com/Sarcasm/compdb.git#egg=compdb

With setuptools::

  python setup.py install


Running the tests
~~~~~~~~~~~~~~~~~

To run the tests, type::

  python ./tests/unit


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


.. _clang-tidy: http://clang.llvm.org/extra/clang-tidy/
.. _compdb: https://github.com/Sarcasm/compdb
.. _irony-mode: https://github.com/Sarcasm/irony-mode
.. _libclang: http://clang.llvm.org/doxygen/group__CINDEX.html
.. _pip: https://pip.pypa.io/
.. _repo: https://gerrit.googlesource.com/git-repo/
.. _rtags: https://github.com/Andersbakken/rtags
.. _JSON Compilation Database: http://clang.llvm.org/docs/JSONCompilationDatabase.html
.. _ycmd: https://github.com/Valloric/ycmd
