This test make sure we are using recursion and that the 'other file' is scored.

One good reason to continue use the 'other file scoring' for transitive includes
is that some template header files have an 'other file' which contains the
template instantiation/definition.

Real-life examples of this:
- Boost, with the impl/*.ipp: http://lists.boost.org/Archives/boost/2003/08/51197.php
- libbitcoin, e.g: https://github.com/libbitcoin/libbitcoin/blob/b765631d6125701dcfb8d6c6744f5b15be7a75fd/include/bitcoin/bitcoin/math/hash.hpp#L214
- LLVM has include/llvm/ProfileData/InstrProfData.inc
