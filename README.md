# compdb: the compilation database Swiss army knife

`compdb` is a command line tool that manipulates compilation databases. A
compilation database is a database for compile options, it has records of which
compile options are used to build your code. One such example of compilation
database is the [JSON Compilation Database][clang-compile-db-ref].

`compdb` aims to make it easier for you to run tools on your codebase
by spoon-feeding you the right compile options.

`compdb` is not so much about generating the initial compilation database, this,
is left to other tools, such as `cmake` and `ninja`. It is only a glue between
the initial compilation database and your tool.

## Motivation

With the proliferation of Clang-based tools, it has been apparent that the
compile options are no longer useful uniquely to the compiler. Standalone tools
such as [clang-tidy][clang-tidy-ref] or text editors with
[libclang][libclang-ref] integration have to deal with compile options.

Examples of such tools, dealing with compilation databases are:
[irony-mode][irony-mode-ref], [rtags][rtags-ref] and [ycmd][ycmd-ref].

Based on this evidence, `compdb` came to life. A tool that has knowledge of the
compile options and can share it both to inform the text editor and to run clang
based tool from the shell.

## Getting started

### Installation

`compdb` is a single python file, to install copy it to your PATH.

### Running the tests

To run the test, type:

```
./test/all.py
```

## Contribute

Contributions are always welcome!

Try to be consistent with the actual code, it will ease the review.

## License

This project is licensed under the MIT License.
See [LICENSE.txt](LICENSE.txt) for details.

## Acknowledgments

- [repo][repo-ref]: for its ubiquitous command line interface,
  which served as an inspiration


[clang-compile-db-ref]: http://clang.llvm.org/docs/JSONCompilationDatabase.html "Clang: JSONCompilationDatabase"
[clang-tidy-ref]: http://clang.llvm.org/extra/clang-tidy/ "clang-tidy"
[irony-mode-ref]: https://github.com/Sarcasm/irony-mode "Irony Mode: A C/C++ minor mode for Emacs powered by libclang"
[libclang-ref]: http://clang.llvm.org/doxygen/group__CINDEX.html "libclang: C Interface to Clang"
[repo-ref]: https://gerrit.googlesource.com/git-repo/ "git-repo"
[ycmd-ref]: https://github.com/Valloric/ycmd "ycmd: A code-completion & code-comprehension server"
[rtags-ref]: https://github.com/Andersbakken/rtags "rtags: A c/c++ client/server indexer for c/c++/objc[++]"
