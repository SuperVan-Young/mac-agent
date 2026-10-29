# Evaluation implementation and configuration live under eval/.
include $(dir $(abspath $(lastword $(MAKEFILE_LIST))))eval/Makefile
