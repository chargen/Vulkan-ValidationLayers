#!/usr/bin/env python3
# Copyright (c) 2015-2018 The Khronos Group Inc.
# Copyright (c) 2015-2018 Valve Corporation
# Copyright (c) 2015-2018 LunarG, Inc.
# Copyright (c) 2015-2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Tobin Ehlis <tobine@google.com>
# Author: Dave Houlton <daveh@lunarg.com>

import argparse
import os
import sys
import platform
import json
import re
import csv
import html
from collections import defaultdict

verbose_mode = False
txt_db = False
csv_db = False
html_db = False
txt_filename = "vk_validation_error_database.txt"
csv_filename = "vk_validation_error_database.csv"
html_filename = "vk_validation_error_database.html"
# header_file = '../layers/vk_validation_error_messages.h'
test_file = '../tests/layer_validation_tests.cpp'
vuid_prefixes = ['VUID-', 'UNASSIGNED-']

# Hard-coded flags that could be command line args, if we decide that's useful
# replace KHR vuids with non-KHR during consistency checking
dealias_khr = True
ignore_unassigned = True # These are not found in layer code unless they appear explicitly (most don't), so produce false positives

generated_layer_source_directories = [
'build',
'dbuild',
'release',
]
generated_layer_source_files = [
'parameter_validation.cpp',
'object_tracker.cpp',
]
layer_source_files = [
'../layers/core_validation.cpp',
'../layers/descriptor_sets.cpp',
'../layers/parameter_validation_utils.cpp',
'../layers/object_tracker_utils.cpp',
'../layers/shader_validation.cpp',
'../layers/buffer_validation.cpp',
]

khr_aliases = { 
    'VUID-vkBindBufferMemory2KHR-device-parameter'                                        : 'VUID-vkBindBufferMemory2-device-parameter', 
    'VUID-vkBindBufferMemory2KHR-pBindInfos-parameter'                                    : 'VUID-vkBindBufferMemory2-pBindInfos-parameter', 
    'VUID-vkBindImageMemory2KHR-device-parameter'                                         : 'VUID-vkBindImageMemory2-device-parameter', 
    'VUID-vkBindImageMemory2KHR-pBindInfos-parameter'                                     : 'VUID-vkBindImageMemory2-pBindInfos-parameter', 
    'VUID-vkCmdDispatchBaseKHR-commandBuffer-parameter'                                   : 'VUID-vkCmdDispatchBase-commandBuffer-parameter', 
    'VUID-vkCmdSetDeviceMaskKHR-commandBuffer-parameter'                                  : 'VUID-vkCmdSetDeviceMask-commandBuffer-parameter', 
    'VUID-vkCreateDescriptorUpdateTemplateKHR-device-parameter'                           : 'VUID-vkCreateDescriptorUpdateTemplate-device-parameter', 
    'VUID-vkCreateDescriptorUpdateTemplateKHR-pDescriptorUpdateTemplate-parameter'        : 'VUID-vkCreateDescriptorUpdateTemplate-pDescriptorUpdateTemplate-parameter', 
    'VUID-vkCreateSamplerYcbcrConversionKHR-device-parameter'                             : 'VUID-vkCreateSamplerYcbcrConversion-device-parameter', 
    'VUID-vkCreateSamplerYcbcrConversionKHR-pYcbcrConversion-parameter'                   : 'VUID-vkCreateSamplerYcbcrConversion-pYcbcrConversion-parameter', 
    'VUID-vkDestroyDescriptorUpdateTemplateKHR-descriptorUpdateTemplate-parameter'        : 'VUID-vkDestroyDescriptorUpdateTemplate-descriptorUpdateTemplate-parameter', 
    'VUID-vkDestroyDescriptorUpdateTemplateKHR-descriptorUpdateTemplate-parent'           : 'VUID-vkDestroyDescriptorUpdateTemplate-descriptorUpdateTemplate-parent',
    'VUID-vkDestroyDescriptorUpdateTemplateKHR-device-parameter'                          : 'VUID-vkDestroyDescriptorUpdateTemplate-device-parameter', 
    'VUID-vkDestroySamplerYcbcrConversionKHR-device-parameter'                            : 'VUID-vkDestroySamplerYcbcrConversion-device-parameter', 
    'VUID-vkDestroySamplerYcbcrConversionKHR-ycbcrConversion-parameter'                   : 'VUID-vkDestroySamplerYcbcrConversion-ycbcrConversion-parameter', 
    'VUID-vkDestroySamplerYcbcrConversionKHR-ycbcrConversion-parent'                      : 'VUID-vkDestroySamplerYcbcrConversion-ycbcrConversion-parent',
    'VUID-vkEnumeratePhysicalDeviceGroupsKHR-instance-parameter'                          : 'VUID-vkEnumeratePhysicalDeviceGroups-instance-parameter', 
    'VUID-vkEnumeratePhysicalDeviceGroupsKHR-pPhysicalDeviceGroupProperties-parameter'    : 'VUID-vkEnumeratePhysicalDeviceGroups-pPhysicalDeviceGroupProperties-parameter', 
    'VUID-vkGetBufferMemoryRequirements2KHR-device-parameter'                             : 'VUID-vkGetBufferMemoryRequirements2-device-parameter', 
    'VUID-vkGetDescriptorSetLayoutSupportKHR-device-parameter'                            : 'VUID-vkGetDescriptorSetLayoutSupport-device-parameter', 
    'VUID-vkGetDeviceGroupPeerMemoryFeaturesKHR-device-parameter'                         : 'VUID-vkGetDeviceGroupPeerMemoryFeatures-device-parameter', 
    'VUID-vkGetDeviceGroupPeerMemoryFeaturesKHR-pPeerMemoryFeatures-parameter'            : 'VUID-vkGetDeviceGroupPeerMemoryFeatures-pPeerMemoryFeatures-parameter', 
    'VUID-vkGetImageMemoryRequirements2KHR-device-parameter'                              : 'VUID-vkGetImageMemoryRequirements2-device-parameter', 
    'VUID-vkGetImageSparseMemoryRequirements2KHR-device-parameter'                        : 'VUID-vkGetImageSparseMemoryRequirements2-device-parameter', 
    'VUID-vkGetImageSparseMemoryRequirements2KHR-pSparseMemoryRequirements-parameter'     : 'VUID-vkGetImageSparseMemoryRequirements2-pSparseMemoryRequirements-parameter', 
    'VUID-vkGetPhysicalDeviceExternalBufferPropertiesKHR-physicalDevice-parameter'        : 'VUID-vkGetPhysicalDeviceExternalBufferProperties-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceExternalFencePropertiesKHR-physicalDevice-parameter'         : 'VUID-vkGetPhysicalDeviceExternalFenceProperties-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceExternalSemaphorePropertiesKHR-physicalDevice-parameter'     : 'VUID-vkGetPhysicalDeviceExternalSemaphoreProperties-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceFeatures2KHR-physicalDevice-parameter'                       : 'VUID-vkGetPhysicalDeviceFeatures2-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceFormatProperties2KHR-format-parameter'                       : 'VUID-vkGetPhysicalDeviceFormatProperties2-format-parameter', 
    'VUID-vkGetPhysicalDeviceFormatProperties2KHR-physicalDevice-parameter'               : 'VUID-vkGetPhysicalDeviceFormatProperties2-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceImageFormatProperties2KHR-physicalDevice-parameter'          : 'VUID-vkGetPhysicalDeviceImageFormatProperties2-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceMemoryProperties2KHR-physicalDevice-parameter'               : 'VUID-vkGetPhysicalDeviceMemoryProperties2-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceProperties2KHR-physicalDevice-parameter'                     : 'VUID-vkGetPhysicalDeviceProperties2-physicalDevice-parameter', 
    'VUID-vkGetPhysicalDeviceQueueFamilyProperties2KHR-pQueueFamilyProperties-parameter'  : 'VUID-vkGetPhysicalDeviceQueueFamilyProperties2-pQueueFamilyProperties-parameter', 
    'VUID-vkGetPhysicalDeviceSparseImageFormatProperties2KHR-pProperties-parameter'       : 'VUID-vkGetPhysicalDeviceSparseImageFormatProperties2-pProperties-parameter', 
    'VUID-vkGetPhysicalDeviceSparseImageFormatProperties2KHR-physicalDevice-parameter'    : 'VUID-vkGetPhysicalDeviceSparseImageFormatProperties2-physicalDevice-parameter', 
    'VUID-vkTrimCommandPoolKHR-commandPool-parameter'                                     : 'VUID-vkTrimCommandPool-commandPool-parameter', 
    'VUID-vkTrimCommandPoolKHR-commandPool-parent'                                        : 'VUID-vkTrimCommandPool-commandPool-parent',
    'VUID-vkTrimCommandPoolKHR-device-parameter'                                          : 'VUID-vkTrimCommandPool-device-parameter', 
    'VUID-vkTrimCommandPoolKHR-flags-zerobitmask'                                         : 'VUID-vkTrimCommandPool-flags-zerobitmask',
    'VUID-vkUpdateDescriptorSetWithTemplateKHR-descriptorSet-parameter'                   : 'VUID-vkUpdateDescriptorSetWithTemplate-descriptorSet-parameter', 
    'VUID-vkUpdateDescriptorSetWithTemplateKHR-descriptorUpdateTemplate-parameter'        : 'VUID-vkUpdateDescriptorSetWithTemplate-descriptorUpdateTemplate-parameter', 
    'VUID-vkUpdateDescriptorSetWithTemplateKHR-descriptorUpdateTemplate-parent'           : 'VUID-vkUpdateDescriptorSetWithTemplate-descriptorUpdateTemplate-parent',
    'VUID-vkUpdateDescriptorSetWithTemplateKHR-device-parameter'                          : 'VUID-vkUpdateDescriptorSetWithTemplate-device-parameter' }

def printHelp():
    print ("Usage: python vk_validation_stats.py json_file")
    print ("                                     [ -c ]")
    print ("                                     [-text [<text_out_filename>]]")
    print ("                                     [-csv [<csv_out_filename>]]")
    print ("                                     [-html [<html_out_filename>]]")
    print ("                                     [-verbose]")
    print ("                                     [-help]")
    print ("\n  The vk_validation_stats parses validation layer source files to determine the")
    print ("  set of valid usage checks and tests currently implemented, and generates")
    print ("  coverage values by comparing against the full set of valid usage identifiers")
    print ("  found in the Vulkan-Headers registry file 'validusate.json'")
    print ("\nArguments: ")
    print (" json-file         (required) input registry file 'validusage.json'")
    print (" -c                report consistency warnings")
    print (" -vuid <vuid_name> report status of individual VUID <vuid_name>")
    print (" -todo             report unimplemented VUIDs")
    print (" -text [filename]  output the error database text to <text_database_filename>,")
    print ("                   defaults to 'vk_validation_error_database.txt'")
    print (" -csv [filename]   output the error database in csv to <csv_database_filename>,")
    print ("                   defaults to 'vk_validation_error_database.csv'")
    print (" -html [filename]  output the error database in html to <html_database_filename>,")
    print ("                   defaults to 'vk_validation_error_database.html'")
    print (" -verbose          show your work (to stdout)")

class ValidationJSON:
    def __init__(self, filename):
        self.filename = filename
        self.explicit_vuids = set()
        self.implicit_vuids = set()
        self.all_vuids = set()
        self.vuid_db = {}
        self.apiversion = ""
        self.re_striptags = re.compile('<.*?>')

    def read(self):
        if os.path.isfile(self.filename):
            json_file = open(self.filename, 'r')
            self.json_dict = json.load(json_file)
            json_file.close()
        if len(self.json_dict) == 0:
            print("Error: Could not find, or error loading validusage.json")
            sys.exit(-1)
        try:
            version = self.json_dict['version info']
            validation = self.json_dict['validation']
            self.apiversion = version['api version']
        except:
            print("Error: Failure parsing validusage.json object")
            sys.exit(-1)

        # Parse vuid from json into local databases
        for apiname in validation.keys():
            # print("entrypoint:%s"%apiname)
            db_entry = {'api' : apiname}
            apidict = validation[apiname]
            for ext in apidict.keys():
                # print("ext:%s"%ext)
                db_entry['ext'] = ext
                vlist = apidict[ext]
                for ventry in vlist:
                    vuid_string = ventry['vuid']
                    if (vuid_string[-5:-1].isdecimal()):    
                        self.explicit_vuids.add(vuid_string)    # explicit end in 5 numeric chars
                        db_entry['type'] = 'explicit'
                    else:
                        self.implicit_vuids.add(vuid_string)    # otherwise, implicit
                        db_entry['type'] = 'implicit'
                    vuid_text = ventry['text']
                    stripped = re.sub(self.re_striptags, '', vuid_text) # strip tags
                    stripped = html.unescape(stripped) # unescape html literals (only partially works - because asciiDoctor?)
                    db_entry['text'] = stripped
                    self.vuid_db[vuid_string] = db_entry.copy() # insert a copy in the database
        self.all_vuids = self.explicit_vuids | self.implicit_vuids

class ValidationSource:
    def __init__(self, source_file_list, generated_source_file_list, generated_source_directories):
        self.source_files = source_file_list
        self.generated_source_files = generated_source_file_list
        self.generated_source_dirs = generated_source_directories
        self.vuid_count_dict = {} # dict of vuid values to the count of how much they're used, and location of where they're used
        self.duplicated_checks = 0
        self.explicit_vuids = set()
        self.implicit_vuids = set()
        self.unassigned_vuids = set()
        self.all_vuids = set()

        if len(self.generated_source_files) > 0:
            qualified_paths = []
            for source in self.generated_source_files:
                for build_dir in self.generated_source_dirs:
                    filepath = '../%s/layers/%s' % (build_dir, source)
                    if os.path.isfile(filepath):
                        qualified_paths.append(filepath)
                        break
            if len(self.generated_source_files) != len(qualified_paths):
                print("Error: Unable to locate one or more of the following source files in the %s directories" % (", ".join(generated_source_directories)))
                print(self.generated_source_files)
                print("Failed to locate one or more codegen files in layer source code - cannot proceed.")
                exit(1)
            else:
                self.source_files.extend(qualified_paths)

    def parse(self):
        prepend = None
        for sf in self.source_files:
            line_num = 0
            with open(sf) as f:
                for line in f:
                    line_num = line_num + 1
                    if True in [line.strip().startswith(comment) for comment in ['//', '/*']]:
                        continue
                    # Find vuid strings
                    if prepend != None:
                        line = prepend[:-2] + line.lstrip().lstrip('"') # join lines skipping CR, whitespace and trailing/leading quote char
                        prepend = None
                    if any(prefix in line for prefix in vuid_prefixes):
                        line_list = line.split()

                        # A VUID string that has been broken by clang will start with a vuid prefix and end with -, and will be last in the list
                        broken_vuid = line_list[-1].strip('"')
                        if any(broken_vuid.startswith(prefix) for prefix in vuid_prefixes) and broken_vuid.endswith('-'):
                            prepend = line
                            continue
                     
                        vuid_list = []
                        for str in line_list:
                            if any(prefix in str for prefix in vuid_prefixes):
                                vuid_list.append(str.strip(',);{}"'))
                        for vuid in vuid_list:
                            if vuid not in self.vuid_count_dict:
                                self.vuid_count_dict[vuid] = {}
                                self.vuid_count_dict[vuid]['count'] = 1
                                self.vuid_count_dict[vuid]['file_line'] = []
                            else:
                                self.duplicated_checks = self.duplicated_checks + 1
                                self.vuid_count_dict[vuid]['count'] = self.vuid_count_dict[vuid]['count'] + 1
                            self.vuid_count_dict[vuid]['file_line'].append('%s,%d' % (sf, line_num))
        # Sort vuids by type
        for vuid in self.vuid_count_dict.keys():
            if (vuid.startswith('VUID-')):
                if (vuid[-5:-1].isdecimal()):    
                    self.explicit_vuids.add(vuid)    # explicit end in 5 numeric chars
                else:
                    self.implicit_vuids.add(vuid)
            elif (vuid.startswith('UNASSIGNED-')):
                self.unassigned_vuids.add(vuid)
            else:
                print("Confused while parsing VUIDs in layer source code - cannot proceed. (FIXME)")
                exit(-1)
        self.all_vuids = self.explicit_vuids | self.implicit_vuids | self.unassigned_vuids

# Class to parse the validation layer test source and store testnames
class ValidationTests:
    def __init__(self, test_file_list, test_group_name=['VkLayerTest', 'VkPositiveLayerTest', 'VkWsiEnabledLayerTest']):
        self.test_files = test_file_list
        self.test_trigger_txt_list = []
        for tg in test_group_name:
            self.test_trigger_txt_list.append('TEST_F(%s' % tg)
        self.explicit_vuids = set()
        self.implicit_vuids = set()
        self.unassigned_vuids = set()
        self.all_vuids = set()
        #self.test_to_vuids = {} # Map test name to VUIDs tested
        self.vuid_to_tests = defaultdict(set) # Map VUIDs to list of test names where implemented

    # Parse test files into internal data struct
    def parse(self):
        # For each test file, parse test names into set
        grab_next_line = False # handle testname on separate line than wildcard
        testname = ''
        prepend = None
        for test_file in self.test_files:
            with open(test_file) as tf:
                for line in tf:
                    if True in [line.strip().startswith(comment) for comment in ['//', '/*']]:
                        continue

                    # if line ends in a broken VUID string, fix that before proceeding
                    if prepend != None:
                        line = prepend[:-2] + line.lstrip().lstrip('"') # join lines skipping CR, whitespace and trailing/leading quote char
                        prepend = None
                    if any(prefix in line for prefix in vuid_prefixes):
                        line_list = line.split()

                        # A VUID string that has been broken by clang will start with a vuid prefix and end with -, and will be last in the list
                        broken_vuid = line_list[-1].strip('"')
                        if any(broken_vuid.startswith(prefix) for prefix in vuid_prefixes) and broken_vuid.endswith('-'):
                            prepend = line
                            continue
                     
                    if any(ttt in line for ttt in self.test_trigger_txt_list):
                        testname = line.split(',')[-1]
                        testname = testname.strip().strip(' {)')
                        #print('Inserting test: "%s"' % (testname))
                        if ('' == testname):
                            grab_next_line = True
                            continue
                        #self.test_to_vuids[testname] = []
                    if grab_next_line: # test name on its own line
                        grab_next_line = False
                        testname = testname.strip().strip(' {)')
                        #self.test_to_vuids[testname] = []
                    if any(prefix in line for prefix in vuid_prefixes):
                        line_list = re.split('[\s{}[\]()"]+',line)
                        for sub_str in line_list:
                            if any(prefix in sub_str for prefix in vuid_prefixes):
                                vuid_str = sub_str.strip(',);:"')
                                self.vuid_to_tests[vuid_str].add(testname)
                                #self.test_to_vuids[testname].append(vuid_str)
                                if (vuid_str.startswith('VUID-')):
                                    if (vuid_str[-5:-1].isdecimal()):    
                                        self.explicit_vuids.add(vuid_str)    # explicit end in 5 numeric chars
                                    else:
                                        self.implicit_vuids.add(vuid_str)
                                elif (vuid_str.startswith('UNASSIGNED-')):
                                    self.unassigned_vuids.add(vuid_str)
                                else:
                                    print("Your script is broken, test parsing: %s" % vuid_str)
                                    exit(-1)
        self.all_vuids = self.explicit_vuids | self.implicit_vuids | self.unassigned_vuids

# Class to do consistency checking
#
class Consistency:
    def __init__(self, all_json, all_checks, all_tests):
        self.valid = all_json
        self.checks = all_checks
        self.tests = all_tests

        # self.valid.add('VUID-Undefined') # Consider undefined a valid VUID

        if (dealias_khr):
            dk = set()
            for vuid in self.checks:
                if vuid in khr_aliases:
                    dk.add(khr_aliases[vuid])
                else:
                    dk.add(vuid)
                self.checks = dk

            dk = set()
            for vuid in self.tests:
                if vuid in khr_aliases:
                    dk.add(khr_aliases[vuid])
                else:
                    dk.add(vuid)
                self.tests = dk

    # Report undefined VUIDs in source code
    def undef_vuids_in_layer_code(self):
        undef_set = self.checks - self.valid
        undef_set.discard('VUID-Undefined') # don't report Undefined
        if ignore_unassigned:
            unassigned = set()
            for vuid in undef_set:
                if vuid.startswith('UNASSIGNED-'): 
                    unassigned.add(vuid)
            undef_set = undef_set - unassigned
        if (len(undef_set) > 0):
            print("\nFollowing VUIDs found in layer code are not defined in validusage.json (%d):" % len(undef_set))
            undef = list(undef_set)
            undef.sort()
            for vuid in undef:
                print("    %s" % vuid)
            return False
        return True

    # Report undefined VUIDs in tests
    def undef_vuids_in_tests(self):
        undef_set = self.tests - self.valid
        undef_set.discard('VUID-Undefined') # don't report Undefined
        if ignore_unassigned:
            unassigned = set()
            for vuid in undef_set:
                if vuid.startswith('UNASSIGNED-'): 
                    unassigned.add(vuid)
            undef_set = undef_set - unassigned
        if (len(undef_set) > 0):
            ok = False
            print("\nFollowing VUIDs found in layer tests are not defined in validusage.json (%d):" % len(undef_set))
            undef = list(undef_set)
            undef.sort()
            for vuid in undef:
                print("    %s" % vuid)
            return False
        return True

    # Report vuids in tests that are not in source
    def vuids_tested_not_checked(self):
        undef_set = self.tests - self.checks
        undef_set.discard('VUID-Undefined') # don't report Undefined
        if ignore_unassigned:
            unassigned = set()
            for vuid in undef_set:
                if vuid.startswith('UNASSIGNED-'): 
                    unassigned.add(vuid)
            undef_set = undef_set - unassigned
        if (len(undef_set) > 0):
            ok = False
            print("\nFollowing VUIDs found in tests but are not checked in layer code (%d):" % len(undef_set))
            undef = list(undef_set)
            undef.sort()
            for vuid in undef:
                print("    %s" % vuid)
            return False
        return True

    # TODO: Explicit checked VUIDs which have no test
    # def explicit_vuids_checked_not_tested(self):


# Class to output database in various flavors
#
class OutputDatabase:
    def __init__(self, val_json, val_source, val_tests):
        self.vj = val_json
        self.vs = val_source
        self.vt = val_tests
    
    def dump_txt(self):
        print("\n Dumping database to text file: %s" % txt_filename)
        with open (txt_filename, 'w') as txt:
            txt.write("## VUID Database\n")
            txt.write("## Format: vuid_name ~^~ checked ~^~ test ~^~ type ~^~ api/struct ~^~ extension ~^~ vuid_text\n##\n") 
            vuid_list = list(self.vj.all_vuids)
            vuid_list.sort()
            for vuid in vuid_list:
                #if '00040' in vuid:
                #    print("Extracting: %s" % vuid)
                #    print(self.vj.vuid_db[vuid])
                checked = 'N'
                if vuid in self.vs.all_vuids:
                    checked = 'Y'
                test = 'None'
                if vuid in self.vt.vuid_to_tests:
                    sep = ', '
                    test = sep.join(self.vt.vuid_to_tests[vuid])

                txt.write("%s~^~%s~^~%s~^~%s~^~%s~^~%s~^~%s\n" % (vuid, checked, test, self.vj.vuid_db[vuid]['type'], self.vj.vuid_db[vuid]['api'], self.vj.vuid_db[vuid]['ext'], self.vj.vuid_db[vuid]['text']))

    def dump_csv(self):
        print("\n Dumping database to csv file: %s" % csv_filename)
        with open (csv_filename, 'w', newline='') as csvfile:
            cw = csv.writer(csvfile)
            cw.writerow(['VUID_NAME','CHECKED','TEST','TYPE','API/STRUCT','EXTENSION','VUID_TEXT']) 
            vuid_list = list(self.vj.all_vuids)
            vuid_list.sort()
            for vuid in vuid_list:
                row = [vuid]
                if vuid in self.vs.all_vuids:
                    row.append('Y')
                else:
                    row.append('N')
                test = 'None'
                if vuid in self.vt.vuid_to_tests:
                    sep = ', '
                    test = sep.join(self.vt.vuid_to_tests[vuid])
                row.append(test)
                row.append(self.vj.vuid_db[vuid]['type'])
                row.append(self.vj.vuid_db[vuid]['api'])
                row.append(self.vj.vuid_db[vuid]['ext'])
                row.append(self.vj.vuid_db[vuid]['text'])
                cw.writerow(row)

    def dump_html(self):
        print("\n Dumping database to html file: %s" % html_filename)
        preamble = '<!DOCTYPE html>\n<html>\n<head>\n<style>\ntable, th, td {\n border: 1px solid black;\n border-collapse: collapse; \n}\n</style>\n<body>\n<h2>Valid Usage Database</h2>\n<font size="2" face="Arial">\n<table style="width:100%">\n'
        headers = '<tr><th>VUID NAME</th><th>CHECKED</th><th>TEST</th><th>TYPE</th><th>API/STRUCT</th><th>EXTENSION</th><th>VUID TEXT</th></tr>\n' 
        with open (html_filename, 'w') as hfile:
            hfile.write(preamble)
            #hfile.write(style)
            hfile.write(headers)
            vuid_list = list(self.vj.all_vuids)
            vuid_list.sort()
            for vuid in vuid_list:
                hfile.write('<tr><th>%s</th>' % vuid)
                checked = '<span style="color:red;">N</span>'
                if vuid in self.vs.all_vuids:
                    checked = '<span style="color:limegreen;">Y</span>'
                hfile.write('<th>%s</th>' % checked)
                test = 'None'
                if vuid in self.vt.vuid_to_tests:
                    sep = ', '
                    test = sep.join(self.vt.vuid_to_tests[vuid])
                hfile.write('<th>%s</th>' % test)
                hfile.write('<th>%s</th>' % self.vj.vuid_db[vuid]['type'])
                hfile.write('<th>%s</th>' % self.vj.vuid_db[vuid]['api'])
                hfile.write('<th>%s</th>' % self.vj.vuid_db[vuid]['ext'])
                hfile.write('<th>%s</th></tr>\n' % self.vj.vuid_db[vuid]['text'])
            hfile.write('</table>\n</body>\n</html>\n')

# Little helper class for coloring cmd line output
class bcolors:

    def __init__(self):
        self.GREEN = '\033[0;32m'
        self.RED = '\033[0;31m'
        self.YELLOW = '\033[1;33m'
        self.ENDC = '\033[0m'
        if 'Linux' != platform.system():
            self.GREEN = ''
            self.RED = ''
            self.YELLOW = ''
            self.ENDC = ''

    def green(self):
        return self.GREEN

    def red(self):
        return self.RED

    def yellow(self):
        return self.YELLOW

    def endc(self):
        return self.ENDC

def main(argv):
    global verbose_mode
    global txt_filename
    global csv_filename
    global html_filename

    run_consistency = False
    report_unimplemented = False
    get_vuid_status = ''
    txt_out = False
    csv_out = False
    html_out = False
    
    if (1 > len(argv)):
        printHelp()
        sys.exit()

    # Parse script args
    json_filename = argv[0]    
    i = 1
    while (i < len(argv)):
        arg = argv[i]
        i = i + 1
        if (arg == '-c'):
            run_consistency = True
        elif (arg == '-vuid'):
            get_vuid_status = argv[i]
            i = i + 1
        elif (arg == '-todo'):
            report_unimplemented = True
        elif (arg == '-txt'):
            txt_out = True
            # Set filename if supplied, else use default
            if i < len(argv) and not argv[i].startswith('-'):
                txt_filename = argv[i]
                i = i + 1
        elif (arg == '-csv'):
            csv_out = True
            # Set filename if supplied, else use default
            if i < len(argv) and not argv[i].startswith('-'):
                csv_filename = argv[i]
                i = i + 1
        elif (arg == '-html'):
            html_out = True
            # Set filename if supplied, else use default
            if i < len(argv) and not argv[i].startswith('-'):
                html_filename = argv[i]
                i = i + 1
        elif (arg in ['-verbose']):
            verbose_mode = True
        elif (arg in ['-help', '-h']):
            printHelp()
            sys.exit()
        else:
            print("Unrecognized argument: %s\n" % arg)
            printHelp()
            sys.exit()

    result = 0 # Non-zero result indicates an error case

    # Parse validusage json
    val_json = ValidationJSON(json_filename)
    val_json.read()
    exp_json = len(val_json.explicit_vuids)
    imp_json = len(val_json.implicit_vuids)
    all_json = len(val_json.all_vuids)
    if verbose_mode:
        print("Found %d unique error vuids in validusage.json file." % all_json)
        print("  %d explicit" % exp_json)
        print("  %d implicit" % imp_json)

    # Parse layer source files
    val_source = ValidationSource(layer_source_files, generated_layer_source_files, generated_layer_source_directories)
    val_source.parse()
    exp_checks = len(val_source.explicit_vuids)
    imp_checks = len(val_source.implicit_vuids)
    all_checks = len(val_source.vuid_count_dict.keys())
    if verbose_mode:
        print("Found %d unique vuid checks in layer source code." % all_checks)
        print("  %d explicit" % exp_checks)
        print("  %d implicit" % imp_checks)
        print("  %d unassigned" % len(val_source.unassigned_vuids))
        print("  %d checks are implemented more that once" % val_source.duplicated_checks)

    # Parse test files
    val_tests = ValidationTests([test_file, ])
    val_tests.parse()
    exp_tests = len(val_tests.explicit_vuids)
    imp_tests = len(val_tests.implicit_vuids)
    all_tests = len(val_tests.all_vuids)
    if verbose_mode:
        print("Found %d unique error vuids in test file %s." % (all_tests, test_file))
        print("  %d explicit" % exp_tests)
        print("  %d implicit" % imp_tests)
        print("  %d unassigned" % len(val_tests.unassigned_vuids))

    # Process stats
    print("\nValidation Statistics (using validusage.json from Vulkan Headers %s)" % val_json.apiversion)
    print("  VUIDs defined in JSON file:  %04d explicit, %04d implicit, %04d total." % (exp_json, imp_json, all_json))
    print("  VUIDs checked in layer code: %04d explicit, %04d implicit, %04d total." % (exp_checks, imp_checks, all_checks))
    print("  VUIDs tested in layer tests: %04d explicit, %04d implicit, %04d total." % (exp_tests, imp_tests, all_tests))
     
    print("\nVUID check coverage")
    print("  Explicit VUIDs checked: %.1f%% (%d checked vs %d defined)" % ((100.0 * exp_checks / exp_json), exp_checks, exp_json))
    print("  Implicit VUIDs checked: %.1f%% (%d checked vs %d defined)" % ((100.0 * imp_checks / imp_json), imp_checks, imp_json))
    print("  Overall VUIDs checked:  %.1f%% (%d checked vs %d defined)" % ((100.0 * all_checks / all_json), all_checks, all_json))

    print("\nVUID test coverage")
    print("  Explicit VUIDs tested: %.1f%% (%d tested vs %d checks)" % ((100.0 * exp_tests / exp_checks), exp_tests, exp_checks))
    print("  Implicit VUIDs tested: %.1f%% (%d tested vs %d checks)" % ((100.0 * imp_tests / imp_checks), imp_tests, imp_checks))
    print("  Overall VUIDs tested:  %.1f%% (%d tested vs %d checks)" % ((100.0 * all_tests / all_checks), all_tests, all_checks))

    # Report status of a single VUID
    if len(get_vuid_status) > 1:
        print("\n\nChecking status of <%s>" % get_vuid_status);
        if get_vuid_status not in val_json.all_vuids:
            print('  Not a valid VUID string.')
        else:
            if get_vuid_status in val_source.explicit_vuids:
                print('  Implemented!')
                line_list = val_source.vuid_count_dict[get_vuid_status]['file_line']
                for line in line_list:
                    print('    => %s' % line)
            else:
                print('  Not implemented.')
            if get_vuid_status in val_tests.explicit_vuids:
                print('  Has a test!')
                test_list = val_tests.vuid_to_tests[get_vuid_status]
                for test in test_list:
                    print('    => %s' % test)
            else:
                print('  Not tested.')

    # Report unimplemented explicit VUIDs
    if report_unimplemented:
        unim_explicit = val_json.explicit_vuids - val_source.explicit_vuids
        print("\n\n%d explicit VUIDs remain unimplemented:" % len(unim_explicit))
        ulist = list(unim_explicit)
        ulist.sort()
        for vuid in ulist:
            print("  => %s" % vuid) 

    # Consistency tests
    if run_consistency:
        print("\n\nRunning consistency tests...")
        con = Consistency(val_json.all_vuids, val_source.all_vuids, val_tests.all_vuids)
        ok = con.undef_vuids_in_layer_code()
        ok &= con.undef_vuids_in_tests()
        ok &= con.vuids_tested_not_checked() 

        if ok:
            print("  OK! No inconsistencies found.")

    # Output database in requested format(s)
    db_out = OutputDatabase(val_json, val_source, val_tests)
    if txt_out:
        db_out.dump_txt()
    if csv_out:
        db_out.dump_csv()
    if html_out:
        db_out.dump_html()

    return result

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

