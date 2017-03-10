LOCAL_PATH := $(abspath $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST)))))

# Customizable variables start here

OUT_DIR=out
COMPDB=python $(LOCAL_PATH)/../../../compdb

# Customizable variables end here

# Optional user configuration can override the default settings
-include local.mk

BUILD_DIR := $(OUT_DIR)/build
DOWNLOAD_DIR := $(OUT_DIR)/dl
SOURCE_DIR := $(OUT_DIR)/src
STAMP_DIR := $(OUT_DIR)/stamp

STAMP_TYPES := download source configure headerdb verify

# Make sure none of the targets are considered intermediate
.PRECIOUS: $(foreach X,$(STAMP_TYPES),$(STAMP_DIR)/%.$X)

# Disable builtin stuff.
.SUFFIXES:

abbreviate_path = $(patsubst $(CURDIR)/%,./%,$1)
abbreviate_exe_path = $(patsubst $(CURDIR)/%,./%,$1)

PROJECTS := \
	cmake \
	irony \
	llvm

# Project specific variables
#
# Mandatory variables:
#   <pkg>_URL
# Optional variables:
#   <pkg>_ARCHIVE_NAME
#   <pkg>_CMAKELIST_SUBDIR
#   <pkg>_SUPPRESSIONS

cmake_URL := https://cmake.org/files/v3.6/cmake-3.6.1.tar.gz
cmake_SUPPRESSIONS := $(LOCAL_PATH)/cmake.supp

irony_URL := https://github.com/Sarcasm/irony-mode/archive/v0.2.0.tar.gz
irony_ARCHIVE_NAME := irony-mode-0.2.0.tar.gz
irony_CMAKELIST_SUBDIR := server/
irony_SUPPRESSIONS := $(LOCAL_PATH)/irony.supp

llvm_URL := http://llvm.org/releases/3.8.1/llvm-3.8.1.src.tar.xz
llvm_SUPPRESSIONS := $(LOCAL_PATH)/llvm.supp

archive_name = $(firstword $($1_ARCHIVE_NAME) $(notdir $($1_URL)))
archive_path = $(DOWNLOAD_DIR)/$(call archive_name,$1)
archive_noext = $(basename $(subst .tar.,.tar,$(call archive_name,$1)))
source_path = $(SOURCE_DIR)/$(call archive_noext,$1)
build_path = $(BUILD_DIR)/$(call archive_noext,$1)

define USAGE
Usage: $(MAKE) [all|project]

Test headerdb on a handful of open source projects.

Available projects: $(PROJECTS)

Targets:
  all       Download, configure, generate compilation database, generate
            header compilation database and verify the header compilation
            database results.
  clean     Clean but preserve downloaded artifacts.
  cleanall  Clean everything.
  help      [Default] Show this message.

Customizable variables (local.mk and command line):
  OUT_DIR  Where to put generated files (default: out)
endef

.PHONY: help
help:
	@: $(info $(USAGE))

.PHONY: all
all: $(PROJECTS)

# New line definition, please keep the two and only two empty lines in the macro
define endl


endef

# declare phony targets for each step for each projects
# make irony-download, make-irony-configure, ...
define project_targets_template
.PHONY: $1
$1: $(STAMP_DIR)/$(1).verify
.PHONY: $(foreach X,$(STAMP_TYPES),$(1)-$(X))
$(foreach X,$(STAMP_TYPES),
.PHONY: $(1)-$(X)$(endl)
$(1)-$(X): $(STAMP_DIR)/$(1).$(X)$(endl))
endef
$(foreach P,$(PROJECTS),$(eval $(call project_targets_template,$(P))))

.PHONY: clean cleanall
clean:
	rm -rf $(BUILD_DIR) $(SOURCE_DIR) $(STAMP_DIR)

cleanall:
	rm -rf $(OUT_DIR)

# order-only prerequisite targets
$(BUILD_DIR) $(DOWNLOAD_DIR) $(SOURCE_DIR) $(STAMP_DIR):
	@mkdir -p $@

$(STAMP_DIR)/%.verify: $(STAMP_DIR)/%.headerdb
	$(COMPDB) -p $(call build_path,$*) -c compdb.complementers=headerdb check -g header \
		$(foreach SUPP,$($*_SUPPRESSIONS),\
			--suppressions $(call abbreviate_path,$(SUPP))) \
		$(call source_path,$*)
	@touch $@

$(STAMP_DIR)/%.headerdb: $(STAMP_DIR)/%.configure
	$(COMPDB) -p $(call build_path,$*) -c compdb.complementers=headerdb update
	@touch $@

$(STAMP_DIR)/%.configure: $(STAMP_DIR)/%.source
	@mkdir -p $(call build_path,$*)
	cd $(call build_path,$*) && \
		cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
			$(abspath $(call source_path,$*))/$($*_CMAKELIST_SUBDIR)
	@touch $@

$(STAMP_DIR)/%.source: $(STAMP_DIR)/%.download | $(SOURCE_DIR)
	tar xf $(call archive_path,$*) -C $(SOURCE_DIR)
	@touch $@

# TODO: could verify md5sum
$(STAMP_DIR)/%.download: | $(STAMP_DIR) $(DOWNLOAD_DIR)
	wget --quiet --continue "$($*_URL)" -O $(call archive_path,$*)
	@touch $@
