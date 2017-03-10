import compdb


class ComplementerInterface(object):
    """Provides a method to compute a compilation datbase complement.

    .. seealso:: complement()
    """

    def complement(self, layers):
        """Compute the complements of multiple layers of databases.

        This method should provide compile commands of files not present in the
        compilations databases but that are part of the same project.

        Multiple databases are passed as argument so that the complementer has
        the opportunity to reduce duplicates and assign each file to the most
        fitting database.

        Example use case #1:
        Imagine a build system with one build directory/compdb per target,
        3 targets:
        1. libfoo      Foo.h (header-only, no foo.cpp to take options from)
        2. foo-test    FooTest.cpp (tests Foo.h, best candidate for the
                       compile options)
        3. foo-example main.cpp
                       Includes Foo.h but is not a very good fit compared to
                       FooTest.cpp in #2

        Example use case #2:
        A multi-compdb project has:
        - headers in project A
        - project B includes project A headers

        In this multi-project setup, the complementer should have
        the opportunity to complement project A's database with the headers
        over project B which uses the headers "more indirectly".
        """
        raise compdb.NotImplementedError
