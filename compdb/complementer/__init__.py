import compdb


class ComplementerInterface(object):
    """Provides a method to compute a compilation datbase complement.

    .. seealso:: complement()
    """

    @property
    def name(self):
        """A short name of the form [a-z]+(_[a-z]+)*."""
        raise compdb.NotImplementedError

    def complement(self, databases):
        """Compute the complements of a multiple databases.

        This method should provide compile commands of files not present in the
        compilations databases but that are part of the same project.

        Multiple databases are passed as argument so that the complementer has
        the opportunity to reduce duplicates and assign each file to the most
        fitting database.
        """
        raise compdb.NotImplementedError
