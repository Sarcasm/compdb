# ZSH completion plugin

To install, add the `functions/` directory to your `fpath`.

This is done automatically if you use one of the numerous ZSH plugin managers.


## check-all-helps: monitor CLI interface changes

The `check-all-helps` monitors the `compdb` help outputs.
When a change is detected it suggest to update files that may depend on it.

To run, type:

    ./check-all-helps
