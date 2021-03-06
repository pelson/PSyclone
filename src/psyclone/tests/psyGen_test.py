# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2017-2018, Science and Technology Facilities Council
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
# Authors R. W. Ford and A. R. Porter STFC Daresbury Lab
# Modified I. Kavcic, Met Office
# -----------------------------------------------------------------------------

''' Performs py.test tests on the psygen module '''


# internal classes requiring tests
# PSy,Invokes,Dependencies,NameSpaceFactory,NameSpace,Invoke,Node,Schedule,
# LoopDirective,OMPLoopDirective,Loop,Call,Inf,SetInfCall,Kern,Arguments,
# InfArguments,Argument,KernelArgument,InfArgument

# user classes requiring tests
# PSyFactory, TransInfo, Transformation
from __future__ import absolute_import, print_function
import os
import re
import pytest
from fparser import api as fpapi
from psyclone_test_utils import get_invoke
from psyclone.psyGen import TransInfo, Transformation, PSyFactory, NameSpace, \
    NameSpaceFactory, OMPParallelDoDirective, PSy, \
    OMPParallelDirective, OMPDoDirective, OMPDirective, Directive, CodeBlock, \
    Assignment, Reference, BinaryOperation, Array, Literal, Node, IfBlock, \
    KernelSchedule, Symbol, SymbolTable
from psyclone.psyGen import Fparser2ASTProcessor
from psyclone.psyGen import GenerationError, FieldNotFoundError, \
     InternalError, HaloExchange, Invoke, DataAccess
from psyclone.dynamo0p3 import DynKern, DynKernMetadata, DynSchedule
from psyclone.parse import parse, InvokeCall
from psyclone.transformations import OMPParallelLoopTrans, \
    DynamoLoopFuseTrans, Dynamo0p3RedundantComputationTrans
from psyclone.generator import generate
from psyclone.configuration import Config

BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "test_files", "dynamo0p3")
GOCEAN_BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "test_files", "gocean1p0")


# Module fixtures

@pytest.fixture(scope="module")
def f2008_parser():
    '''Initialize fparser2 with Fortran2008 standard'''
    from fparser.two.parser import ParserFactory
    return ParserFactory().create(std="f2008")

# PSyFactory class unit tests


def test_invalid_api():
    '''test that psyfactory raises appropriate error when an invalid api
    is supplied'''
    with pytest.raises(GenerationError):
        _ = PSyFactory(api="invalid")


def test_psyfactory_valid_return_object():
    '''test that psyfactory returns a psyfactory object for all supported
    inputs'''
    psy_factory = PSyFactory()
    assert isinstance(psy_factory, PSyFactory)
    from psyclone.configuration import Config
    _config = Config.get()
    apis = _config.supported_apis[:]
    apis.insert(0, "")
    for api in apis:
        psy_factory = PSyFactory(api=api)
        assert isinstance(psy_factory, PSyFactory)


def test_psyfactory_valid_dm_flag():
    '''test that a PSyFactory instance raises an exception if the
    optional distributed_memory flag is set to an invalid value
    and does not if the value is valid '''
    with pytest.raises(GenerationError) as excinfo:
        _ = PSyFactory(distributed_memory="ellie")
    assert "distributed_memory flag" in str(excinfo.value)
    _ = PSyFactory(distributed_memory=True)
    _ = PSyFactory(distributed_memory=False)


# PSy class unit tests

def test_psy_base_err(monkeypatch):
    ''' Check that we cannot call gen or psy_module on the base class
    directly '''
    # We have no easy way to create the extra information which
    # the PSy constructor requires. Therefore, we use a PSyFactory
    # object and monkey-patch it so that it has a name attribute.
    factory = PSyFactory()
    monkeypatch.setattr(factory, "name",
                        value="fred", raising=False)
    psy = PSy(factory)
    with pytest.raises(NotImplementedError) as excinfo:
        _ = psy.gen
    assert "must be implemented by subclass" in str(excinfo)


# Transformation class unit tests

def test_base_class_not_callable():
    '''make sure we can not instantiate abstract Transformation class
    directly'''
    with pytest.raises(TypeError):
        _ = Transformation()  # pylint: disable=abstract-class-instantiated


# TransInfo class unit tests

def test_new_module():
    '''check that we can change the module where we look for
    transformations.  There should be no transformations
    available as the new module uses a different
    transformation base class'''
    from test_files import dummy_transformations
    trans = TransInfo(module=dummy_transformations)
    assert trans.num_trans == 0


def test_new_baseclass():
    '''check that we can change the transformations baseclass. There
    should be no transformations available as the default
    transformations module does not use the specified base
    class'''
    from test_files.dummy_transformations import \
        LocalTransformation
    trans = TransInfo(base_class=LocalTransformation)
    assert trans.num_trans == 0


def test_new_module_and_baseclass():
    '''check that we can change the module where we look for
    transformations and the baseclass. There should be one
    transformation available as the module specifies one test
    transformation using the specified base class '''
    from test_files import dummy_transformations
    trans = TransInfo(module=dummy_transformations,
                      base_class=dummy_transformations.LocalTransformation)
    assert trans.num_trans == 1


def test_list_valid_return_object():
    ''' check the list method returns the valid type '''
    trans = TransInfo()
    assert isinstance(trans.list, str)


def test_list_return_data():
    ''' check the list method returns sensible information '''
    trans = TransInfo()
    assert trans.list.find("available") != -1


def test_invalid_low_number():
    '''check an out-of-range low number for get_trans_num method raises
    correct exception'''
    trans = TransInfo()
    with pytest.raises(GenerationError):
        _ = trans.get_trans_num(0)


def test_invalid_high_number():
    '''check an out-of-range high number for get_trans_num method raises
    correct exception'''
    trans = TransInfo()
    with pytest.raises(GenerationError):
        _ = trans.get_trans_num(999)


def test_valid_return_object_from_number():
    ''' check get_trans_num method returns expected type of instance '''
    trans = TransInfo()
    transform = trans.get_trans_num(1)
    assert isinstance(transform, Transformation)


def test_invalid_name():
    '''check get_trans_name method fails correctly when an invalid name
    is provided'''
    trans = TransInfo()
    with pytest.raises(GenerationError):
        _ = trans.get_trans_name("invalid")


def test_valid_return_object_from_name():
    ''' check get_trans_name method return the correct object type '''
    trans = TransInfo()
    transform = trans.get_trans_name("LoopFuse")
    assert isinstance(transform, Transformation)


# NameSpace class unit tests

def test_fail_context_label():
    '''check an error is raised if one of context and label is not None'''
    namespace = NameSpace()
    with pytest.raises(RuntimeError):
        namespace.create_name(context="dummy_context")
    with pytest.raises(RuntimeError):
        namespace.create_name(label="dummy_context")


def test_case_sensitive_names():
    ''' tests that in the case sensitive option, names that only differ by
    case are treated as being distinct'''
    namespace_cs = NameSpace(case_sensitive=True)
    name = "Rupert"
    name1 = namespace_cs.create_name(root_name=name)
    name2 = namespace_cs.create_name(root_name=name.lower())
    assert name1 == name
    assert name2 == name.lower()


def test_case_insensitive_names():
    ''' tests that in the case insensitive option (the default), names that
    only differ by case are treated as being the same '''
    namespace = NameSpace()
    name = "Rupert"
    name1 = namespace.create_name(root_name=name)
    name2 = namespace.create_name(root_name=name.lower())
    assert name1 == name.lower()
    assert name2 == name1 + "_1"


def test_new_labels():
    '''tests that different labels and contexts are treated as being
    distinct'''
    namespace = NameSpace()
    name = "Rupert"
    name1 = namespace.create_name(root_name=name, context="home",
                                  label="me")
    name2 = namespace.create_name(root_name=name, context="work",
                                  label="me")
    name3 = namespace.create_name(root_name=name, context="home",
                                  label="a bear")
    name4 = namespace.create_name(root_name=name, context="work",
                                  label="a bear")
    assert name1 == name.lower()
    assert name2 == name1+"_1"
    assert name3 == name1+"_2"
    assert name4 == name1+"_3"


def test_new_labels_case_sensitive():
    '''tests that different labels and contexts are treated as being
    distinct for case sensitive names'''
    namespace = NameSpace(case_sensitive=True)
    name = "Rupert"
    name1 = namespace.create_name(root_name=name, context="home",
                                  label="me")
    name2 = namespace.create_name(root_name=name, context="work",
                                  label="me")
    name3 = namespace.create_name(root_name=name, context="home",
                                  label="Me")
    name4 = namespace.create_name(root_name=name, context="Work",
                                  label="me")
    assert name1 == name
    assert name2 == name1+"_1"
    assert name3 == name1+"_2"
    assert name4 == name1+"_3"


def test_existing_labels():
    '''tests that existing labels and contexts return the previous name'''
    namespace = NameSpace()
    name = "Rupert"
    name1 = namespace.create_name(root_name=name, context="home",
                                  label="me")
    name2 = namespace.create_name(root_name=name, context="work",
                                  label="me")
    name3 = namespace.create_name(root_name=name, context="home",
                                  label="Me")
    name4 = namespace.create_name(root_name=name, context="Work",
                                  label="me")
    assert name1 == name.lower()
    assert name2 == name1+"_1"
    assert name3 == name1
    assert name4 == name2


def test_existing_labels_case_sensitive():
    '''tests that existing labels and contexts return the previous name'''
    namespace = NameSpace(case_sensitive=True)
    name = "Rupert"
    name1 = namespace.create_name(root_name=name, context="home",
                                  label="me")
    name2 = namespace.create_name(root_name=name, context="Work",
                                  label="Me")
    name3 = namespace.create_name(root_name=name, context="home",
                                  label="me")
    name4 = namespace.create_name(root_name=name, context="Work",
                                  label="Me")
    assert name1 == name
    assert name2 == name1+"_1"
    assert name3 == name1
    assert name4 == name2


def test_reserved_names():
    '''tests that reserved names are not returned by the name space
    manager'''
    namea = "PSyclone"
    nameb = "Dynamo"
    namespace = NameSpace()
    namespace.add_reserved_name(namea)
    name1 = namespace.create_name(root_name=namea.lower())
    assert name1 == namea.lower()+"_1"
    namespace.add_reserved_names([nameb.lower()])
    name1 = namespace.create_name(root_name=nameb)
    assert name1 == nameb.lower()+"_1"


def test_reserved_names_case_sensitive():
    '''tests that reserved names are not returned by the case sensitive
    name space manager'''
    namea = "PSyclone"
    nameb = "Dynamo"
    namespace = NameSpace(case_sensitive=True)
    namespace.add_reserved_name(namea)
    name1 = namespace.create_name(root_name=namea)
    assert name1 == namea+"_1"
    name1 = namespace.create_name(root_name=namea.lower())
    assert name1 == namea.lower()
    namespace.add_reserved_names([nameb])
    name1 = namespace.create_name(root_name=nameb)
    assert name1 == nameb+"_1"
    name1 = namespace.create_name(root_name=nameb.lower())
    assert name1 == nameb.lower()


def test_reserved_name_exists():
    '''tests that an error is generated if a reserved name has already
    been used as a name'''
    name = "PSyclone"
    namespace = NameSpace()
    _ = namespace.create_name(root_name=name)
    with pytest.raises(RuntimeError):
        namespace.add_reserved_name(name)
    with pytest.raises(RuntimeError):
        namespace.add_reserved_name(name.lower())


def test_reserved_name_exists_case_sensitive():
    '''tests that an error is generated if a reserved name has already
    been used as a name'''
    name = "PSyclone"
    namespace = NameSpace(case_sensitive=True)
    _ = namespace.create_name(root_name=name)
    namespace.add_reserved_name(name.lower())
    with pytest.raises(RuntimeError):
        namespace.add_reserved_name(name)
    with pytest.raises(RuntimeError):
        namespace.add_reserved_names([name])


def test_anonymous_name():
    ''' tests that anonymous names are successfully created '''
    namespace = NameSpace()
    name1 = namespace.create_name()
    assert name1 == "anon"
    name2 = namespace.create_name()
    assert name2 == "anon_1"


def test_internal_name_clashes():
    ''' tests that names that are generated internally by the namespace
    manager can be used as root names'''
    anon_name = "Anon"
    namespace = NameSpace()
    name1 = namespace.create_name()
    name2 = namespace.create_name(root_name=anon_name)
    assert name1 == anon_name.lower()
    assert name2 == name1+"_1"
    name3 = namespace.create_name(root_name=anon_name+"_1")
    assert name3 == name2+"_1"


def test_intern_name_clash_case_sensitive():
    '''tests that names that are generated internally by the case
    sensitive namespace manager can be used as root names'''
    anon_name = "Anon"
    namespace = NameSpace(case_sensitive=True)
    _ = namespace.create_name()
    name2 = namespace.create_name(root_name=anon_name)
    assert name2 == anon_name
    name3 = namespace.create_name(root_name=anon_name.lower())
    assert name3 == anon_name.lower()+"_1"


# tests that the NameSpaceFactory class is working correctly

def test_create():
    '''tests that a NameSpace object is returned from the create method'''
    nsf = NameSpaceFactory()
    nspace = nsf.create()
    assert isinstance(nspace, NameSpace)


def test_singleton():
    '''test that the same NameSpace object is returned from different
    NameSpaceFactory's by default'''
    nsf = NameSpaceFactory()
    ns1 = nsf.create()
    nsf = NameSpaceFactory()
    ns2 = nsf.create()
    assert ns1 == ns2


def test_reset():
    ''' test that different NameSpace objects are returned from different
    NameSpaceFactory's when the reset option is set'''
    nsf = NameSpaceFactory()
    ns1 = nsf.create()
    nsf = NameSpaceFactory(reset=True)
    ns2 = nsf.create()
    assert ns1 != ns2

# tests for class Call


def test_invokes_can_always_be_printed():
    '''Test that an Invoke instance can always be printed (i.e. is
    initialised fully)'''
    inv = Invoke(None, None, None)
    assert inv.__str__() == "invoke()"

    invoke_call = InvokeCall([], "TestName")
    inv = Invoke(invoke_call, 12, DynSchedule)
    # Name is converted to lower case if set in constructor of InvokeCall:
    assert inv.__str__() == "invoke_testname()"

    invoke_call._name = None
    inv = Invoke(invoke_call, 12, DynSchedule)
    assert inv.__str__() == "invoke_12()"

    # Last test case: one kernel call - to avoid constructing
    # the InvokeCall, parse an existing Fortran file"

    _, invoke = parse(
        os.path.join(BASE_PATH, "1.12_single_invoke_deref_name_clash.f90"),
        api="dynamo0.3")

    alg_invocation = list(invoke.calls.values())[0]
    inv = Invoke(alg_invocation, 0, DynSchedule)
    assert inv.__str__() == \
        "invoke_0_testkern_type(a, f1_my_field, f1%my_field, m1, m2)"


def test_same_name_invalid():
    '''test that we raise an error if the same name is passed into the
    same kernel or built-in instance. We need to choose a particular
    API to check this although the code is in psyGen.py '''
    with pytest.raises(GenerationError) as excinfo:
        _, _ = generate(
            os.path.join(BASE_PATH, "1.10_single_invoke_same_name.f90"),
            api="dynamo0.3")
    assert ("Argument 'f1' is passed into kernel 'testkern_code' code "
            "more than once") in str(excinfo.value)


def test_same_name_invalid_array():
    '''test that we raise an error if the same name is passed into the
    same kernel or built-in instance. In this case arguments have
    array references and mixed case. We need to choose a particular
    API to check this although the code is in psyGen.py. '''
    with pytest.raises(GenerationError) as excinfo:
        _, _ = generate(
            os.path.join(BASE_PATH, "1.11_single_invoke_same_name_array.f90"),
            api="dynamo0.3")
    assert ("Argument 'f1(1, n)' is passed into kernel 'testkern_code' code "
            "more than once") in str(excinfo.value)


def test_derived_type_deref_naming():
    ''' Test that we do not get a name clash for dummy arguments in the PSy
    layer when the name generation for the component of a derived type
    may lead to a name already taken by another argument. '''
    _, invoke = parse(
        os.path.join(BASE_PATH, "1.12_single_invoke_deref_name_clash.f90"),
        api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke)
    generated_code = str(psy.gen)
    print(generated_code)
    output = (
        "    SUBROUTINE invoke_0_testkern_type"
        "(a, f1_my_field, f1_my_field_1, m1, m2)\n"
        "      USE testkern, ONLY: testkern_code\n"
        "      USE mesh_mod, ONLY: mesh_type\n"
        "      REAL(KIND=r_def), intent(in) :: a\n"
        "      TYPE(field_type), intent(inout) :: f1_my_field\n"
        "      TYPE(field_type), intent(in) :: f1_my_field_1, m1, m2\n")
    assert output in generated_code


FAKE_KERNEL_METADATA = '''
module dummy_mod
  type, extends(kernel_type) :: dummy_type
     type(arg_type), meta_args(3) =                    &
          (/ arg_type(gh_field, gh_write,     w3),     &
             arg_type(gh_field, gh_readwrite, wtheta), &
             arg_type(gh_field, gh_inc,       w1)      &
           /)
     integer :: iterates_over = cells
   contains
     procedure, nopass :: code => dummy_code
  end type dummy_type
contains
  subroutine dummy_code()
  end subroutine dummy_code
end module dummy_mod
'''

# Schedule class tests


def test_sched_view(capsys):
    ''' Check the view method of the Schedule class. We need a Schedule
    object for this so go via the dynamo0.3 sub-class '''
    from psyclone import dynamo0p3
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "15.9.1_X_innerproduct_Y_builtin.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    super(dynamo0p3.DynSchedule, psy.invokes.invoke_list[0].schedule).view()
    output, _ = capsys.readouterr()
    assert colored("Schedule", SCHEDULE_COLOUR_MAP["Schedule"]) in output


def test_sched_ocl_setter():
    ''' Check that the opencl setter raises the expected error if not passed
    a bool. '''
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "15.9.1_X_innerproduct_Y_builtin.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    with pytest.raises(ValueError) as err:
        psy.invokes.invoke_list[0].schedule.opencl = "a string"
    assert "Schedule.opencl must be a bool but got " in str(err)


# Kern class test

def test_kern_get_kernel_schedule():
    ''' Tests the get_kernel_schedule method in the Kern class.
    '''
    ast = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=False)
    metadata = DynKernMetadata(ast)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    schedule = my_kern.get_kernel_schedule()
    assert isinstance(schedule, KernelSchedule)


def test_kern_class_view(capsys):
    ''' Tests the view method in the Kern class. The simplest way to
    do this is via the dynamo0.3 subclass '''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    ast = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=False)
    metadata = DynKernMetadata(ast)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    my_kern.view()
    out, _ = capsys.readouterr()
    expected_output = (
        colored("KernCall", SCHEDULE_COLOUR_MAP["KernCall"]) +
        " dummy_code(field_1,field_2,field_3) [module_inline=False]")
    assert expected_output in out


def test_kern_coloured_text():
    ''' Check that the coloured_text method of Kern returns what we expect '''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    ast = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=False)
    metadata = DynKernMetadata(ast)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    ret_str = my_kern.coloured_text
    assert colored("KernCall", SCHEDULE_COLOUR_MAP["KernCall"]) in ret_str


def test_kern_abstract_methods():
    ''' Check that the abstract methods of the Kern class raise the
    NotImplementedError. '''
    # We need to get a valid kernel object
    from psyclone import dynamo0p3
    ast = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=False)
    metadata = DynKernMetadata(ast)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    with pytest.raises(NotImplementedError) as err:
        super(dynamo0p3.DynKern, my_kern).gen_arg_setter_code(None)
    assert "gen_arg_setter_code must be implemented by sub-class" in str(err)


def test_call_abstract_methods():
    ''' Check that calling the abstract methods of Call raises
    the expected exceptions '''
    from psyclone.psyGen import Call, Arguments
    my_arguments = Arguments(None)

    class KernType(object):  # pylint: disable=too-few-public-methods
        ''' temporary dummy class '''
        def __init__(self):
            self.iterates_over = "stuff"
    my_ktype = KernType()

    class DummyClass(object):  # pylint: disable=too-few-public-methods
        ''' temporary dummy class '''
        def __init__(self, ktype):
            self.module_name = "dummy_module"
            self.ktype = ktype

    dummy_call = DummyClass(my_ktype)
    my_call = Call(None, dummy_call, "dummy", my_arguments)
    with pytest.raises(NotImplementedError) as excinfo:
        my_call.local_vars()
    assert "Call.local_vars should be implemented" in str(excinfo.value)

    with pytest.raises(NotImplementedError) as excinfo:
        my_call.__str__()
    assert "Call.__str__ should be implemented" in str(excinfo.value)

    with pytest.raises(NotImplementedError) as excinfo:
        my_call.gen_code(None)
    assert "Call.gen_code should be implemented" in str(excinfo.value)


def test_arguments_abstract():
    ''' Check that we raise NotImplementedError if any of the virtual methods
    of the Arguments class are called. '''
    from psyclone.psyGen import Arguments
    my_arguments = Arguments(None)
    with pytest.raises(NotImplementedError) as err:
        _ = my_arguments.acc_args
    assert "Arguments.acc_args must be implemented in sub-class" in str(err)
    with pytest.raises(NotImplementedError) as err:
        _ = my_arguments.scalars
    assert "Arguments.scalars must be implemented in sub-class" in str(err)
    with pytest.raises(NotImplementedError) as err:
        _ = my_arguments.raw_arg_list()
    assert ("Arguments.raw_arg_list must be implemented in sub-class"
            in str(err))


def test_incremented_arg():
    ''' Check that we raise the expected exception when
    Kern.incremented_arg() is called for a kernel that does not have
    an argument that is incremented '''
    from psyclone.psyGen import Kern
    # Change the kernel metadata so that the the incremented kernel
    # argument has read access
    import fparser
    fparser.logging.disable(fparser.logging.CRITICAL)
    # If we change the meta-data then we trip the check in the parser.
    # Therefore, we change the object produced by parsing the meta-data
    # instead
    ast = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=False)
    metadata = DynKernMetadata(ast)
    for descriptor in metadata.arg_descriptors:
        if descriptor.access == "gh_inc":
            descriptor._access = "gh_read"
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    with pytest.raises(FieldNotFoundError) as excinfo:
        Kern.incremented_arg(my_kern, mapping={"inc": "gh_inc"})
    assert ("does not have an argument with gh_inc access"
            in str(excinfo.value))


def test_written_arg():
    ''' Check that we raise the expected exception when
    Kern.written_arg() is called for a kernel that does not have
    an argument that is written or readwritten to '''
    from psyclone.psyGen import Kern
    # Change the kernel metadata so that the only kernel argument has
    # read access
    import fparser
    fparser.logging.disable(fparser.logging.CRITICAL)
    # If we change the meta-data then we trip the check in the parser.
    # Therefore, we change the object produced by parsing the meta-data
    # instead
    ast = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=False)
    metadata = DynKernMetadata(ast)
    for descriptor in metadata.arg_descriptors:
        if descriptor.access in ["gh_write", "gh_readwrite"]:
            descriptor._access = "gh_read"
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    with pytest.raises(FieldNotFoundError) as excinfo:
        Kern.written_arg(my_kern,
                         mapping={"write": "gh_write",
                                  "readwrite": "gh_readwrite"})
    assert ("does not have an argument with gh_write or "
            "gh_readwrite access" in str(excinfo.value))


def test_ompdo_constructor():
    ''' Check that we can make an OMPDoDirective with and without
    children '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "1_single_invoke.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.invoke_list[0].schedule
    ompdo = OMPDoDirective(parent=schedule)
    assert not ompdo.children
    ompdo = OMPDoDirective(parent=schedule, children=[schedule.children[0]])
    assert len(ompdo.children) == 1


def test_ompdo_directive_class_view(capsys):
    '''tests the view method in the OMPDoDirective class. We create a
    sub-class object then call this method from it '''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    _, invoke_info = parse(os.path.join(BASE_PATH, "1_single_invoke.f90"),
                           api="dynamo0.3")

    cases = [
        {"current_class": OMPParallelDoDirective,
         "current_string": "[OMP parallel do]"},
        {"current_class": OMPDoDirective, "current_string": "[OMP do]"},
        {"current_class": OMPParallelDirective,
         "current_string": "[OMP parallel]"},
        {"current_class": OMPDirective, "current_string": "[OMP]"},
        {"current_class": Directive, "current_string": ""}]
    otrans = OMPParallelLoopTrans()
    for case in cases:
        for dist_mem in [False, True]:

            psy = PSyFactory("dynamo0.3", distributed_memory=dist_mem).\
                create(invoke_info)
            schedule = psy.invokes.invoke_list[0].schedule

            if dist_mem:
                idx = 3
            else:
                idx = 0

            _, _ = otrans.apply(schedule.children[idx])
            omp_parallel_loop = schedule.children[idx]

            # call the OMPDirective view method
            case["current_class"].view(omp_parallel_loop)

            out, _ = capsys.readouterr()
            expected_output = (
                colored("Directive", SCHEDULE_COLOUR_MAP["Directive"]) +
                case["current_string"] + "\n"
                "    "+colored("Loop", SCHEDULE_COLOUR_MAP["Loop"]) +
                "[type='',field_space='w1',it_space='cells', "
                "upper_bound='ncells']\n"
                "        "+colored("KernCall",
                                   SCHEDULE_COLOUR_MAP["KernCall"]) +
                " testkern_code(a,f1,f2,m1,m2) "
                "[module_inline=False]")
            print(out)
            print(expected_output)
            assert expected_output in out


def test_acc_dir_view(capsys):
    ''' Test the view() method of OpenACC directives '''
    from psyclone.transformations import ACCDataTrans, ACCLoopTrans, \
        ACCParallelTrans
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP

    acclt = ACCLoopTrans()
    accdt = ACCDataTrans()
    accpt = ACCParallelTrans()

    _, invoke = get_invoke("single_invoke.f90", "gocean1.0", idx=0)
    colour = SCHEDULE_COLOUR_MAP["Directive"]
    schedule = invoke.schedule
    # Enter-data
    new_sched, _ = accdt.apply(schedule)
    # Artificially add a child to this directive so as to get full
    # coverage of the associated view() method
    new_sched.children[0].addchild(new_sched.children[1])
    new_sched.children[0].view()
    out, _ = capsys.readouterr()
    assert out.startswith(
        colored("Directive", colour)+"[ACC enter data]")

    # Parallel region
    new_sched, _ = accpt.apply(new_sched.children[1])
    new_sched.children[1].view()
    out, _ = capsys.readouterr()
    assert out.startswith(
        colored("Directive", colour)+"[ACC Parallel]")

    # Loop directive
    new_sched, _ = acclt.apply(new_sched.children[1].children[0])
    new_sched.children[1].children[0].view()
    out, _ = capsys.readouterr()
    assert out.startswith(
        colored("Directive", colour)+"[ACC Loop, independent]")

    # Loop directive with collapse
    new_sched, _ = acclt.apply(new_sched.children[1].children[0].children[0],
                               collapse=2)
    new_sched.children[1].children[0].children[0].view()
    out, _ = capsys.readouterr()
    assert out.startswith(
        colored("Directive", colour)+"[ACC Loop, collapse=2, independent]")


def test_haloexchange_unknown_halo_depth():
    '''test the case when the halo exchange base class is called without
    a halo depth'''
    halo_exchange = HaloExchange(None)
    assert halo_exchange._halo_depth is None


def test_globalsum_view(capsys):
    '''test the view method in the GlobalSum class. The simplest way to do
    this is to use a dynamo0p3 builtin example which contains a scalar and
    then call view() on that.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    from psyclone import dynamo0p3
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "15.9.1_X_innerproduct_Y_builtin.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    psy.invokes.invoke_list[0].schedule.view()
    output, _ = capsys.readouterr()
    print(output)
    expected_output = (colored("GlobalSum",
                               SCHEDULE_COLOUR_MAP["GlobalSum"]) +
                       "[scalar='asum']")
    assert expected_output in output
    gsum = None
    for child in psy.invokes.invoke_list[0].schedule.children:
        if isinstance(child, dynamo0p3.DynGlobalSum):
            gsum = child
            break
    assert gsum
    ret_str = super(dynamo0p3.DynGlobalSum, gsum).coloured_text
    assert colored("GlobalSum", SCHEDULE_COLOUR_MAP["GlobalSum"]) in ret_str


def test_args_filter():
    '''the args_filter() method is in both Loop() and Arguments() classes
    with the former method calling the latter. This example tests the
    case when unique is set to True and therefore any replicated names
    are not returned. The simplest way to do this is to use a
    dynamo0p3 example which includes two kernels which share argument
    names. We choose dm=False to make it easier to fuse the loops.'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "1.2_multi_invoke.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=False).create(invoke_info)
    # fuse our loops so we have more than one Kernel in a loop
    schedule = psy.invokes.invoke_list[0].schedule
    ftrans = DynamoLoopFuseTrans()
    schedule, _ = ftrans.apply(schedule.children[0],
                               schedule.children[1])
    # get our loop and call our method ...
    loop = schedule.children[0]
    args = loop.args_filter(unique=True)
    expected_output = ["a", "f1", "f2", "m1", "m2", "f3"]
    for arg in args:
        assert arg.name in expected_output
    assert len(args) == len(expected_output)


def test_args_filter2():
    '''the args_filter() method is in both Loop() and Arguments() classes
    with the former method calling the latter. This example tests the cases
    when one or both of the intent and type arguments are not specified.'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "10_operator.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    schedule = psy.invokes.invoke_list[0].schedule
    loop = schedule.children[3]

    # arg_accesses
    args = loop.args_filter(arg_accesses=["gh_read"])
    expected_output = ["chi", "a"]
    for arg in args:
        assert arg.name in expected_output
    assert len(args) == len(expected_output)

    # arg_types
    args = loop.args_filter(arg_types=["gh_operator", "gh_integer"])
    expected_output = ["mm_w0", "a"]
    for arg in args:
        assert arg.name in expected_output
    assert len(args) == len(expected_output)

    # neither
    args = loop.args_filter()
    expected_output = ["chi", "mm_w0", "a"]
    for arg in args:
        assert arg.name in expected_output
    assert len(args) == len(expected_output)


def test_reduction_var_error():
    '''Check that we raise an exception if the zero_reduction_variable()
    method is provided with an incorrect type of argument'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "1_single_invoke.f90"),
                           api="dynamo0.3")
    for dist_mem in [False, True]:
        psy = PSyFactory("dynamo0.3",
                         distributed_memory=dist_mem).create(invoke_info)
        schedule = psy.invokes.invoke_list[0].schedule
        call = schedule.calls()[0]
        # args[1] is of type gh_field
        call._reduction_arg = call.arguments.args[1]
        with pytest.raises(GenerationError) as err:
            call.zero_reduction_variable(None)
        assert ("zero_reduction variable should be one of ['gh_real', "
                "'gh_integer']") in str(err)


def test_reduction_sum_error():
    '''Check that we raise an exception if the reduction_sum_loop()
    method is provided with an incorrect type of argument'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "1_single_invoke.f90"),
                           api="dynamo0.3")
    for dist_mem in [False, True]:
        psy = PSyFactory("dynamo0.3",
                         distributed_memory=dist_mem).create(invoke_info)
        schedule = psy.invokes.invoke_list[0].schedule
        call = schedule.calls()[0]
        # args[1] is of type gh_field
        call._reduction_arg = call.arguments.args[1]
        with pytest.raises(GenerationError) as err:
            call.reduction_sum_loop(None)
        assert (
            "unsupported reduction access 'gh_write' found in DynBuiltin:"
            "reduction_sum_loop(). Expected one of '['gh_sum']") in str(err)


def test_call_multi_reduction_error(monkeypatch):
    '''Check that we raise an exception if we try to create a Call (a
    Kernel or a Builtin) with more than one reduction in it. Since we have
    a rule that only Builtins can write to scalars we need a built-in that
    attempts to perform two reductions. '''
    from psyclone import dynamo0p3_builtins
    monkeypatch.setattr(dynamo0p3_builtins, "BUILTIN_DEFINITIONS_FILE",
                        value=os.path.join(BASE_PATH,
                                           "multi_reduction_builtins_mod.f90"))
    for dist_mem in [False, True]:
        _, invoke_info = parse(
            os.path.join(BASE_PATH, "16.4.1_multiple_scalar_sums2.f90"),
            api="dynamo0.3", distributed_memory=dist_mem)
        with pytest.raises(GenerationError) as err:
            _ = PSyFactory("dynamo0.3",
                           distributed_memory=dist_mem).create(invoke_info)
        assert (
            "PSyclone currently only supports a single reduction in a kernel "
            "or builtin" in str(err))


def test_invoke_name():
    ''' Check that specifying the name of an invoke in the Algorithm
    layer results in a correctly-named routine in the PSy layer '''
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "1.0.1_single_named_invoke.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    gen = str(psy.gen)
    print(gen)
    assert "SUBROUTINE invoke_important_invoke" in gen


def test_multi_kern_named_invoke():
    ''' Check that specifying the name of an invoke containing multiple
    kernel invocations result in a correctly-named routine in the PSy layer '''
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "4.9_named_multikernel_invokes.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    gen = str(psy.gen)
    print(gen)
    assert "SUBROUTINE invoke_some_name" in gen


def test_named_multi_invokes():
    ''' Check that we generate correct code when we have more than one
    named invoke in an Algorithm file '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH,
                     "3.2_multi_functions_multi_named_invokes.f90"),
        api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    gen = str(psy.gen)
    print(gen)
    assert "SUBROUTINE invoke_my_first(" in gen
    assert "SUBROUTINE invoke_my_second(" in gen


def test_named_invoke_name_clash():
    ''' Check that we do not get a name clash when the name of a variable
    in the PSy layer would normally conflict with the name given to the
    subroutine generated by an Invoke. '''
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "4.11_named_invoke_name_clash.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    gen = str(psy.gen)
    print(gen)
    assert "SUBROUTINE invoke_a(invoke_a_1, b, c, istp, rdt," in gen
    assert "TYPE(field_type), intent(inout) :: invoke_a_1" in gen


def test_invalid_reprod_pad_size(monkeypatch):
    '''Check that we raise an exception if the pad size in psyclone.cfg is
    set to an invalid value '''
    # Make sure we monkey patch the correct Config object
    from psyclone.configuration import Config
    monkeypatch.setattr(Config._instance, "_reprod_pad_size", 0)
    for distmem in [True, False]:
        _, invoke_info = parse(
            os.path.join(BASE_PATH,
                         "15.9.1_X_innerproduct_Y_builtin.f90"),
            distributed_memory=distmem,
            api="dynamo0.3")
        psy = PSyFactory("dynamo0.3",
                         distributed_memory=distmem).create(invoke_info)
        invoke = psy.invokes.invoke_list[0]
        schedule = invoke.schedule
        from psyclone.transformations import Dynamo0p3OMPLoopTrans, \
            OMPParallelTrans
        otrans = Dynamo0p3OMPLoopTrans()
        rtrans = OMPParallelTrans()
        # Apply an OpenMP do directive to the loop
        schedule, _ = otrans.apply(schedule.children[0], reprod=True)
        # Apply an OpenMP Parallel directive around the OpenMP do directive
        schedule, _ = rtrans.apply(schedule.children[0])
        invoke.schedule = schedule
        with pytest.raises(GenerationError) as excinfo:
            _ = str(psy.gen)
        assert (
            "REPROD_PAD_SIZE in {0} should be a positive "
            "integer".format(Config.get().filename) in str(excinfo.value))


def test_argument_depends_on():
    '''Check that the depends_on method returns the appropriate boolean
    value for arguments with combinations of read and write access'''
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "4.5_multikernel_invokes.f90"),
                           distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    arg_f1_inc_1 = schedule.children[0].children[0].arguments.args[0]
    arg_f1_inc_2 = schedule.children[2].children[0].arguments.args[0]
    arg_f2_read_1 = schedule.children[0].children[0].arguments.args[2]
    arg_f2_inc = schedule.children[1].children[0].arguments.args[0]
    arg_f2_read_2 = schedule.children[2].children[0].arguments.args[1]
    # different names returns False
    assert not arg_f2_inc._depends_on(arg_f1_inc_1)
    # same name both reads returns False
    assert not arg_f2_read_1._depends_on(arg_f2_read_2)
    # same name both incs (write to read) returns True
    assert arg_f1_inc_2._depends_on(arg_f1_inc_1)
    # read to write returns True
    assert arg_f2_read_1._depends_on(arg_f2_inc)
    # write to read returns True
    assert arg_f2_inc._depends_on(arg_f2_read_1)
    # same name both writes (the 4.5 example only uses inc) returns True
    _, invoke_info = parse(
        os.path.join(BASE_PATH,
                     "15.14.4_builtin_and_normal_kernel_invoke.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    arg_f1_write_1 = schedule.children[0].children[0].arguments.args[1]
    arg_f1_write_2 = schedule.children[1].children[0].arguments.args[0]
    assert arg_f1_write_1._depends_on(arg_f1_write_2)


def test_argument_find_argument():
    '''Check that the find_argument method returns the first dependent
    argument in a list of nodes, or None if none are found'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # 1: returns none if none found
    f1_first_read = schedule.children[0].children[0].arguments.args[2]
    # a) empty node list
    assert not f1_first_read._find_argument([])
    # b) check many reads
    call_nodes = schedule.calls()
    assert not f1_first_read._find_argument(call_nodes)
    # 2: returns first dependent kernel arg when there are many
    # dependencies (check first read returned)
    f3_write = schedule.children[3].children[0].arguments.args[0]
    f3_first_read = schedule.children[0].children[0].arguments.args[3]
    result = f3_write._find_argument(call_nodes)
    assert result == f3_first_read
    # 3: haloexchange node
    _, invoke_info = parse(
        os.path.join(BASE_PATH,
                     "15.14.4_builtin_and_normal_kernel_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # a) kern arg depends on halo arg
    m2_read_arg = schedule.children[3].children[0].arguments.args[4]
    m2_halo_field = schedule.children[2].field
    result = m2_read_arg._find_argument(schedule.children)
    assert result == m2_halo_field
    # b) halo arg depends on kern arg
    result = m2_halo_field._find_argument([schedule.children[3].children[0]])
    assert result == m2_read_arg
    # 4: globalsum node
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # a) globalsum arg depends on kern arg
    kern_asum_arg = schedule.children[3].children[0].arguments.args[1]
    glob_sum_arg = schedule.children[2].scalar
    result = kern_asum_arg._find_argument(schedule.children)
    assert result == glob_sum_arg
    # b) kern arg depends on globalsum arg
    result = glob_sum_arg._find_argument([schedule.children[3].children[0]])
    assert result == kern_asum_arg


def test_argument_find_read_arguments():
    '''Check that the find_read_arguments method returns the appropriate
    arguments in a list of nodes.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # 1: returns [] if not a writer. f1 is read, not written.
    f1_first_read = schedule.children[0].children[0].arguments.args[2]
    call_nodes = schedule.calls()
    assert f1_first_read._find_read_arguments(call_nodes) == []
    # 2: return list of readers (f3 is written to and then read by
    # three following calls)
    f3_write = schedule.children[3].children[0].arguments.args[0]
    result = f3_write._find_read_arguments(call_nodes[4:])
    assert len(result) == 3
    for idx in range(3):
        loop = schedule.children[idx+4]
        assert result[idx] == loop.children[0].arguments.args[3]
    # 3: Return empty list if no readers (f2 is written to but not
    # read)
    f2_write = schedule.children[0].children[0].arguments.args[0]
    assert f2_write._find_read_arguments(call_nodes[1:]) == []
    # 4: Return list of readers before a subsequent writer
    f3_write = schedule.children[3].children[0].arguments.args[0]
    result = f3_write._find_read_arguments(call_nodes)
    assert len(result) == 3
    for idx in range(3):
        loop = schedule.children[idx]
        assert result[idx] == loop.children[0].arguments.args[3]


def test_globalsum_arg():
    ''' Check that the globalsum argument is defined as gh_readwrite and
    points to the GlobalSum node '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    glob_sum = schedule.children[2]
    glob_sum_arg = glob_sum.scalar
    assert glob_sum_arg.access == "gh_readwrite"
    assert glob_sum_arg.call == glob_sum


def test_haloexchange_arg():
    '''Check that the HaloExchange argument is defined as gh_readwrite and
    points to the HaloExchange node'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH,
                     "15.14.4_builtin_and_normal_kernel_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    halo_exchange = schedule.children[2]
    halo_exchange_arg = halo_exchange.field
    assert halo_exchange_arg.access == "gh_readwrite"
    assert halo_exchange_arg.call == halo_exchange


def test_argument_forward_read_dependencies():
    '''Check that the forward_read_dependencies method returns the appropriate
    arguments in a schedule.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # 1: returns [] if not a writer. f1 is read, not written.
    f1_first_read = schedule.children[0].children[0].arguments.args[2]
    _ = schedule.calls()
    assert f1_first_read.forward_read_dependencies() == []
    # 2: return list of readers (f3 is written to and then read by
    # three following calls)
    f3_write = schedule.children[3].children[0].arguments.args[0]
    result = f3_write.forward_read_dependencies()
    assert len(result) == 3
    for idx in range(3):
        loop = schedule.children[idx+4]
        assert result[idx] == loop.children[0].arguments.args[3]
    # 3: Return empty list if no readers (f2 is written to but not
    # read)
    f2_write = schedule.children[0].children[0].arguments.args[0]
    assert f2_write.forward_read_dependencies() == []


def test_argument_forward_dependence(monkeypatch, annexed):
    '''Check that forward_dependence method returns the first dependent
    argument after the current Node in the schedule or None if none
    are found. We also test when annexed is False and True as it
    affects how many halo exchanges are generated.

    '''
    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    f1_first_read = schedule.children[0].children[0].arguments.args[2]
    # 1: returns none if none found (check many reads)
    assert not f1_first_read.forward_dependence()
    # 2: returns first dependent kernel arg when there are many
    # dependencies (check first read returned)
    f3_write = schedule.children[3].children[0].arguments.args[0]
    f3_next_read = schedule.children[4].children[0].arguments.args[3]
    result = f3_write.forward_dependence()
    assert result == f3_next_read
    # 3: haloexchange dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.5_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    if annexed:
        index = 7
    else:
        index = 8
    f2_prev_arg = schedule.children[index-1].children[0].arguments.args[0]
    f2_halo_field = schedule.children[index].field
    f2_next_arg = schedule.children[index+1].children[0].arguments.args[1]
    # a) previous kern arg depends on halo arg
    result = f2_prev_arg.forward_dependence()
    assert result == f2_halo_field
    # b) halo arg depends on following kern arg
    result = f2_halo_field.forward_dependence()
    assert result == f2_next_arg
    # 4: globalsum dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    prev_arg = schedule.children[0].children[0].arguments.args[1]
    sum_arg = schedule.children[1].children[0].arguments.args[0]
    global_sum_arg = schedule.children[2].scalar
    next_arg = schedule.children[3].children[0].arguments.args[1]
    # a) prev kern arg depends on sum
    result = prev_arg.forward_dependence()
    assert result == sum_arg
    # b) sum arg depends on global sum arg
    result = sum_arg.forward_dependence()
    assert result == global_sum_arg
    # c) global sum arg depends on next kern arg
    result = global_sum_arg.forward_dependence()
    assert result == next_arg


def test_argument_backward_dependence(monkeypatch, annexed):
    '''Check that backward_dependence method returns the first dependent
    argument before the current Node in the schedule or None if none
    are found. We also test when annexed is False and True as it
    affects how many halo exchanges are generated.

    '''
    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    f1_last_read = schedule.children[6].children[0].arguments.args[2]
    # 1: returns none if none found (check many reads)
    assert not f1_last_read.backward_dependence()
    # 2: returns first dependent kernel arg when there are many
    # dependencies (check first read returned)
    f3_write = schedule.children[3].children[0].arguments.args[0]
    f3_prev_read = schedule.children[2].children[0].arguments.args[3]
    result = f3_write.backward_dependence()
    assert result == f3_prev_read
    # 3: haloexchange dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.5_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    if annexed:
        index = 7
    else:
        index = 8
    f2_prev_arg = schedule.children[index-1].children[0].arguments.args[0]
    f2_halo_field = schedule.children[index].field
    f2_next_arg = schedule.children[index+1].children[0].arguments.args[1]
    # a) following kern arg depends on halo arg
    result = f2_next_arg.backward_dependence()
    assert result == f2_halo_field
    # b) halo arg depends on previous kern arg
    result = f2_halo_field.backward_dependence()
    assert result == f2_prev_arg
    # 4: globalsum dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    prev_arg = schedule.children[0].children[0].arguments.args[1]
    sum_arg = schedule.children[1].children[0].arguments.args[0]
    global_sum_arg = schedule.children[2].scalar
    next_arg = schedule.children[3].children[0].arguments.args[1]
    # a) next kern arg depends on global sum arg
    result = next_arg.backward_dependence()
    assert result == global_sum_arg
    # b) global sum arg depends on sum arg
    result = global_sum_arg.backward_dependence()
    assert result == sum_arg
    # c) sum depends on prev kern arg
    result = sum_arg.backward_dependence()
    assert result == prev_arg


def test_node_depth():
    '''Test that the Node class depth method returns the correct value
    for a Node in a tree '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    assert schedule.depth == 1
    for child in schedule.children:
        assert child.depth == 2
    for child in schedule.children[3].children:
        assert child.depth == 3


def test_node_args():
    '''Test that the Node class args method returns the correct arguments
    for Nodes that do not have arguments themselves'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4_multikernel_invokes.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    loop1 = schedule.children[0]
    kern1 = loop1.children[0]
    loop2 = schedule.children[1]
    kern2 = loop2.children[0]
    # 1) Schedule (not that this is useful)
    all_args = kern1.arguments.args
    all_args.extend(kern2.arguments.args)
    schedule_args = schedule.args
    for idx, arg in enumerate(all_args):
        assert arg == schedule_args[idx]
    # 2) Loop1
    loop1_args = loop1.args
    for idx, arg in enumerate(kern1.arguments.args):
        assert arg == loop1_args[idx]
    # 3) Loop2
    loop2_args = loop2.args
    for idx, arg in enumerate(kern2.arguments.args):
        assert arg == loop2_args[idx]
    # 4) Loopfuse
    ftrans = DynamoLoopFuseTrans()
    schedule, _ = ftrans.apply(schedule.children[0], schedule.children[1],
                               same_space=True)
    loop = schedule.children[0]
    kern1 = loop.children[0]
    kern2 = loop.children[1]
    loop_args = loop.args
    kern_args = kern1.arguments.args
    kern_args.extend(kern2.arguments.args)
    for idx, arg in enumerate(kern_args):
        assert arg == loop_args[idx]


def test_call_args():
    '''Test that the call class args method returns the appropriate
    arguments '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH,
                     "15.14.4_builtin_and_normal_kernel_invoke.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    kern = schedule.children[0].children[0]
    builtin = schedule.children[1].children[0]
    # 1) kern
    for idx, arg in enumerate(kern.args):
        assert arg == kern.arguments.args[idx]
    # 2) builtin
    for idx, arg in enumerate(builtin.args):
        assert arg == builtin.arguments.args[idx]


def test_haloexchange_args():
    '''Test that the haloexchange class args method returns the appropriate
    argument '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    for haloexchange in schedule.children[:2]:
        assert len(haloexchange.args) == 1
        assert haloexchange.args[0] == haloexchange.field


def test_globalsum_args():
    '''Test that the globalsum class args method returns the appropriate
    argument '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    global_sum = schedule.children[2]
    assert len(global_sum.args) == 1
    assert global_sum.args[0] == global_sum.scalar


def test_node_forward_dependence():
    '''Test that the Node class forward_dependence method returns the
    closest dependent Node after the current Node in the schedule or
    None if none are found.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    read4 = schedule.children[4]
    # 1: returns none if none found
    # a) check many reads
    assert not read4.forward_dependence()
    # b) check no dependencies for a call
    assert not read4.children[0].forward_dependence()
    # 2: returns first dependent kernel arg when there are many
    # dependencies
    # a) check first read returned
    writer = schedule.children[3]
    next_read = schedule.children[4]
    assert writer.forward_dependence() == next_read
    # a) check writer returned
    first_loop = schedule.children[0]
    assert first_loop.forward_dependence() == writer
    # 3: haloexchange dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.5_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    prev_loop = schedule.children[7]
    halo_field = schedule.children[8]
    next_loop = schedule.children[9]
    # a) previous loop depends on halo exchange
    assert prev_loop.forward_dependence() == halo_field
    # b) halo exchange depends on following loop
    assert halo_field.forward_dependence() == next_loop

    # 4: globalsum dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    prev_loop = schedule.children[0]
    sum_loop = schedule.children[1]
    global_sum_loop = schedule.children[2]
    next_loop = schedule.children[3]
    # a) prev loop depends on sum loop
    assert prev_loop.forward_dependence() == sum_loop
    # b) sum loop depends on global sum loop
    assert sum_loop.forward_dependence() == global_sum_loop
    # c) global sum loop depends on next loop
    assert global_sum_loop.forward_dependence() == next_loop


def test_node_backward_dependence():
    '''Test that the Node class backward_dependence method returns the
    closest dependent Node before the current Node in the schedule or
    None if none are found.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # 1: loop no backwards dependence
    loop3 = schedule.children[2]
    assert not loop3.backward_dependence()
    # 2: loop to loop backward dependence
    # a) many steps
    last_loop_node = schedule.children[6]
    prev_dep_loop_node = schedule.children[3]
    assert last_loop_node.backward_dependence() == prev_dep_loop_node
    # b) previous
    assert prev_dep_loop_node.backward_dependence() == loop3
    # 3: haloexchange dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.5_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    loop2 = schedule.children[7]
    halo_exchange = schedule.children[8]
    loop3 = schedule.children[9]
    # a) following loop node depends on halo exchange node
    result = loop3.backward_dependence()
    assert result == halo_exchange
    # b) halo exchange node depends on previous loop node
    result = halo_exchange.backward_dependence()
    assert result == loop2
    # 4: globalsum dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    loop1 = schedule.children[0]
    loop2 = schedule.children[1]
    global_sum = schedule.children[2]
    loop3 = schedule.children[3]
    # a) loop3 depends on global sum
    assert loop3.backward_dependence() == global_sum
    # b) global sum depends on loop2
    assert global_sum.backward_dependence() == loop2
    # c) loop2 (sum) depends on loop1
    assert loop2.backward_dependence() == loop1


def test_call_forward_dependence():
    '''Test that the Call class forward_dependence method returns the
    closest dependent call after the current call in the schedule or
    None if none are found. This is achieved by loop fusing first.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    ftrans = DynamoLoopFuseTrans()
    for _ in range(6):
        schedule, _ = ftrans.apply(schedule.children[0], schedule.children[1],
                                   same_space=True)
    read4 = schedule.children[0].children[4]
    # 1: returns none if none found
    # a) check many reads
    assert not read4.forward_dependence()
    # 2: returns first dependent kernel arg when there are many
    # dependencies
    # a) check first read returned
    writer = schedule.children[0].children[3]
    next_read = schedule.children[0].children[4]
    assert writer.forward_dependence() == next_read
    # a) check writer returned
    first_loop = schedule.children[0].children[0]
    assert first_loop.forward_dependence() == writer


def test_call_backward_dependence():
    '''Test that the Call class backward_dependence method returns the
    closest dependent call before the current call in the schedule or
    None if none are found. This is achieved by loop fusing first.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    ftrans = DynamoLoopFuseTrans()
    for _ in range(6):
        schedule, _ = ftrans.apply(schedule.children[0], schedule.children[1],
                                   same_space=True)
    # 1: loop no backwards dependence
    call3 = schedule.children[0].children[2]
    assert not call3.backward_dependence()
    # 2: call to call backward dependence
    # a) many steps
    last_call_node = schedule.children[0].children[6]
    prev_dep_call_node = schedule.children[0].children[3]
    assert last_call_node.backward_dependence() == prev_dep_call_node
    # b) previous
    assert prev_dep_call_node.backward_dependence() == call3


def test_omp_forward_dependence():
    '''Test that the forward_dependence method works for Directives,
    returning the closest dependent Node after the current Node in the
    schedule or None if none are found. '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    from psyclone.transformations import DynamoOMPParallelLoopTrans
    otrans = DynamoOMPParallelLoopTrans()
    for child in schedule.children:
        schedule, _ = otrans.apply(child)
    read4 = schedule.children[4]
    # 1: returns none if none found
    # a) check many reads
    assert not read4.forward_dependence()
    # b) check no dependencies for the loop
    assert not read4.children[0].forward_dependence()
    # 2: returns first dependent kernel arg when there are many
    # dependencies
    # a) check first read returned
    writer = schedule.children[3]
    next_read = schedule.children[4]
    assert writer.forward_dependence() == next_read
    # b) check writer returned
    first_omp = schedule.children[0]
    assert first_omp.forward_dependence() == writer
    # 3: directive and globalsum dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    schedule, _ = otrans.apply(schedule.children[0])
    schedule, _ = otrans.apply(schedule.children[1])
    schedule, _ = otrans.apply(schedule.children[3])
    prev_omp = schedule.children[0]
    sum_omp = schedule.children[1]
    global_sum_loop = schedule.children[2]
    next_omp = schedule.children[3]
    # a) prev omp depends on sum omp
    assert prev_omp.forward_dependence() == sum_omp
    # b) sum omp depends on global sum loop
    assert sum_omp.forward_dependence() == global_sum_loop
    # c) global sum loop depends on next omp
    assert global_sum_loop.forward_dependence() == next_omp


def test_directive_backward_dependence():
    '''Test that the backward_dependence method works for Directives,
    returning the closest dependent Node before the current Node in
    the schedule or None if none are found.'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    from psyclone.transformations import DynamoOMPParallelLoopTrans
    otrans = DynamoOMPParallelLoopTrans()
    for child in schedule.children:
        schedule, _ = otrans.apply(child)
    # 1: omp directive no backwards dependence
    omp3 = schedule.children[2]
    assert not omp3.backward_dependence()
    # 2: omp to omp backward dependence
    # a) many steps
    last_omp_node = schedule.children[6]
    prev_dep_omp_node = schedule.children[3]
    assert last_omp_node.backward_dependence() == prev_dep_omp_node
    # b) previous
    assert prev_dep_omp_node.backward_dependence() == omp3
    # 3: globalsum dependencies
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    schedule, _ = otrans.apply(schedule.children[0])
    schedule, _ = otrans.apply(schedule.children[1])
    schedule, _ = otrans.apply(schedule.children[3])
    omp1 = schedule.children[0]
    omp2 = schedule.children[1]
    global_sum = schedule.children[2]
    omp3 = schedule.children[3]
    # a) omp3 depends on global sum
    assert omp3.backward_dependence() == global_sum
    # b) global sum depends on omp2
    assert global_sum.backward_dependence() == omp2
    # c) omp2 (sum) depends on omp1
    assert omp2.backward_dependence() == omp1


def test_directive_get_private(monkeypatch):
    ''' Tests for the _get_private_list() method of OMPParallelDirective. '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # We use Transformations to introduce the necessary directives
    from psyclone.transformations import Dynamo0p3OMPLoopTrans, \
        OMPParallelTrans
    otrans = Dynamo0p3OMPLoopTrans()
    rtrans = OMPParallelTrans()
    # Apply an OpenMP do directive to the loop
    schedule, _ = otrans.apply(schedule.children[0], reprod=True)
    # Apply an OpenMP Parallel directive around the OpenMP do directive
    schedule, _ = rtrans.apply(schedule.children[0])
    directive = schedule.children[0]
    assert isinstance(directive, OMPParallelDirective)
    # Now check that _get_private_list returns what we expect
    pvars = directive._get_private_list()
    assert pvars == ['cell']
    # Now use monkeypatch to break the Call within the loop
    call = directive.children[0].children[0].children[0]
    monkeypatch.setattr(call, "local_vars", lambda: [""])
    with pytest.raises(InternalError) as err:
        _ = directive._get_private_list()
    assert ("call 'testkern_code' has a local variable but its name is "
            "not set" in str(err))


def test_node_is_valid_location():
    '''Test that the Node class is_valid_location method returns True if
    the new location does not break any data dependencies, otherwise it
    returns False'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # 1: new node argument is invalid
    node = schedule.children[0]
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location("invalid_node_argument")
    assert "argument is not a Node, it is a 'str'." in str(excinfo.value)
    # 2: optional position argument is invalid
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location(node, position="invalid_node_argument")
    assert "The position argument in the psyGen" in str(excinfo.value)
    assert "method must be one of" in str(excinfo.value)
    # 3: parents of node and new_node are not the same
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location(schedule.children[3].children[0])
    assert ("the node and the location do not have the same "
            "parent") in str(excinfo.value)
    # 4: positions are the same
    prev_node = schedule.children[0]
    node = schedule.children[1]
    next_node = schedule.children[2]
    # a) before this node
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location(node, position="before")
    assert "the node and the location are the same" in str(excinfo.value)
    # b) after this node
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location(node, position="after")
    assert "the node and the location are the same" in str(excinfo.value)
    # c) after previous node
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location(prev_node, position="after")
    assert "the node and the location are the same" in str(excinfo.value)
    # d) before next node
    with pytest.raises(GenerationError) as excinfo:
        node.is_valid_location(next_node, position="before")
    assert "the node and the location are the same" in str(excinfo.value)
    # 5: valid no previous dependency
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.1_multi_aX_plus_Y_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # 6: valid no prev dep
    node = schedule.children[2]
    assert node.is_valid_location(schedule.children[0])
    # 7: valid prev dep (after)
    node = schedule.children[6]
    assert node.is_valid_location(schedule.children[3], position="after")
    # 8: invalid prev dep (before)
    assert not node.is_valid_location(schedule.children[3], position="before")
    # 9: valid no following dep
    node = schedule.children[4]
    assert node.is_valid_location(schedule.children[6], position="after")
    # 10: valid following dep (before)
    node = schedule.children[0]
    assert node.is_valid_location(schedule.children[3], position="before")
    # 11: invalid following dep (after)
    node = schedule.children[0]
    assert not node.is_valid_location(schedule.children[3], position="after")


def test_node_ancestor():
    ''' Test the Node.ancestor() method '''
    from psyclone.psyGen import Loop
    _, invoke = get_invoke("single_invoke.f90", "gocean1.0", idx=0)
    sched = invoke.schedule
    sched.view()
    kern = sched.children[0].children[0].children[0]
    node = kern.ancestor(Node)
    assert isinstance(node, Loop)
    node = kern.ancestor(Node, excluding=[Loop])
    assert node is sched


def test_dag_names():
    '''test that the dag_name method returns the correct value for the
    node class and its specialisations'''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    from psyclone.psyGen import Schedule
    assert super(Schedule, schedule).dag_name == "node_0"
    assert schedule.dag_name == "schedule"
    assert schedule.children[0].dag_name == "checkhaloexchange(f2)_0"
    assert schedule.children[3].dag_name == "loop_4"
    schedule.children[3].loop_type = "colour"
    assert schedule.children[3].dag_name == "loop_[colour]_4"
    schedule.children[3].loop_type = ""
    assert (schedule.children[3].children[0].dag_name ==
            "kernel_testkern_code_5")
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "15.14.3_sum_setval_field_builtin.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    global_sum = schedule.children[2]
    assert global_sum.dag_name == "globalsum(asum)_2"
    builtin = schedule.children[1].children[0]
    assert builtin.dag_name == "builtin_sum_x_4"


def test_openmp_pdo_dag_name():
    '''Test that we generate the correct dag name for the OpenMP parallel
    do node'''
    _, info = parse(os.path.join(BASE_PATH,
                                 "15.7.2_setval_X_builtin.f90"),
                    api="dynamo0.3", distributed_memory=False)
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    from psyclone.transformations import DynamoOMPParallelLoopTrans
    otrans = DynamoOMPParallelLoopTrans()
    # Apply OpenMP parallelisation to the loop
    schedule, _ = otrans.apply(schedule.children[0])
    assert schedule.children[0].dag_name == "OMP_parallel_do_1"


def test_omp_dag_names():
    '''Test that we generate the correct dag names for omp parallel, omp
    do, omp directive and directive nodes'''
    _, info = parse(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "test_files", "dynamo0p3",
                                 "1_single_invoke.f90"),
                    api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=False).create(info)
    invoke = psy.invokes.get('invoke_0_testkern_type')
    schedule = invoke.schedule
    from psyclone.transformations import Dynamo0p3OMPLoopTrans, \
        OMPParallelTrans
    olooptrans = Dynamo0p3OMPLoopTrans()
    ptrans = OMPParallelTrans()
    # Put an OMP PARALLEL around this loop
    child = schedule.children[0]
    oschedule, _ = ptrans.apply(child)
    # Put an OMP DO around this loop
    schedule, _ = olooptrans.apply(oschedule.children[0].children[0])
    # Replace the original loop schedule with the transformed one
    omp_par_node = schedule.children[0]
    assert omp_par_node.dag_name == "OMP_parallel_1"
    assert omp_par_node.children[0].dag_name == "OMP_do_2"
    omp_directive = super(OMPParallelDirective, omp_par_node)
    assert omp_directive.dag_name == "OMP_directive_1"
    print(type(omp_directive))
    directive = super(OMPDirective, omp_par_node)
    assert directive.dag_name == "directive_1"


def test_acc_dag_names():
    ''' Check that we generate the correct dag names for ACC parallel,
    ACC enter-data and ACC loop directive Nodes '''
    from psyclone.psyGen import ACCDataDirective
    from psyclone.transformations import ACCDataTrans, ACCParallelTrans, \
        ACCLoopTrans
    _, invoke = get_invoke("single_invoke.f90", "gocean1.0", idx=0)
    schedule = invoke.schedule

    acclt = ACCLoopTrans()
    accdt = ACCDataTrans()
    accpt = ACCParallelTrans()
    # Enter-data
    new_sched, _ = accdt.apply(schedule)
    assert schedule.children[0].dag_name == "ACC_data_1"
    # Parallel region
    new_sched, _ = accpt.apply(new_sched.children[1])
    assert schedule.children[1].dag_name == "ACC_parallel_2"
    # Loop directive
    new_sched, _ = acclt.apply(new_sched.children[1].children[0])
    assert schedule.children[1].children[0].dag_name == "ACC_loop_3"
    # Base class
    name = super(ACCDataDirective, schedule.children[0]).dag_name
    assert name == "ACC_directive_1"


def test_acc_datadevice_virtual():
    ''' Check that we can't instantiate an instance of ACCDataDirective. '''
    from psyclone.psyGen import ACCDataDirective
    # pylint:disable=abstract-class-instantiated
    with pytest.raises(TypeError) as err:
        ACCDataDirective()
    # pylint:enable=abstract-class-instantiated
    assert ("instantiate abstract class ACCDataDirective with abstract "
            "methods data_on_device" in str(err))


def test_node_dag_no_graphviz(tmpdir, monkeypatch):
    '''test that dag generation does nothing if graphviz is not
    installed. We monkeypatch sys.modules to ensure that it always
    appears that graphviz is not installed on this system. '''
    import sys
    monkeypatch.setitem(sys.modules, 'graphviz', None)
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    my_file = tmpdir.join('test')
    schedule.dag(file_name=my_file.strpath)
    assert not os.path.exists(my_file.strpath)


# Use a regex to allow for whitespace differences between graphviz
# versions. Need a raw-string (r"") to get new-lines handled nicely.
EXPECTED2 = re.compile(
    r"digraph {\n"
    r"\s*schedule_start\n"
    r"\s*schedule_end\n"
    r"\s*loop_1_start\n"
    r"\s*loop_1_end\n"
    r"\s*loop_1_end -> loop_3_start \[color=green\]\n"
    r"\s*schedule_start -> loop_1_start \[color=blue\]\n"
    r"\s*kernel_testkern_qr_code_2\n"
    r"\s*kernel_testkern_qr_code_2 -> loop_1_end \[color=blue\]\n"
    r"\s*loop_1_start -> kernel_testkern_qr_code_2 \[color=blue\]\n"
    r"\s*loop_3_start\n"
    r"\s*loop_3_end\n"
    r"\s*loop_3_end -> schedule_end \[color=blue\]\n"
    r"\s*loop_1_end -> loop_3_start \[color=red\]\n"
    r"\s*kernel_testkern_qr_code_4\n"
    r"\s*kernel_testkern_qr_code_4 -> loop_3_end \[color=blue\]\n"
    r"\s*loop_3_start -> kernel_testkern_qr_code_4 \[color=blue\]\n"
    r"}")
# pylint: enable=anomalous-backslash-in-string


def test_node_dag(tmpdir, have_graphviz):
    '''test that dag generation works correctly. Skip the test if
    graphviz is not installed'''
    if not have_graphviz:
        return
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.1_multikernel_invokes.f90"),
        distributed_memory=False, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=False).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    my_file = tmpdir.join('test')
    schedule.dag(file_name=my_file.strpath)
    result = my_file.read()
    print(result)
    assert EXPECTED2.match(result)
    my_file = tmpdir.join('test.svg')
    result = my_file.read()
    for name in ["<title>schedule_start</title>",
                 "<title>schedule_end</title>",
                 "<title>loop_1_start</title>",
                 "<title>loop_1_end</title>",
                 "<title>kernel_testkern_qr_code_2</title>",
                 "<title>kernel_testkern_qr_code_4</title>",
                 "<svg", "</svg>", ]:
        assert name in result
    for colour_name, colour_code in [("blue", "#0000ff"),
                                     ("green", "#00ff00"),
                                     ("red", "#ff0000")]:
        assert colour_name in result or colour_code in result

    with pytest.raises(GenerationError) as excinfo:
        schedule.dag(file_name=my_file.strpath, file_format="rubbish")
    assert "unsupported graphviz file format" in str(excinfo.value)


def test_haloexchange_halo_depth_get_set():
    '''test that the halo_exchange getter and setter work correctly '''
    halo_depth = 4
    halo_exchange = HaloExchange(None)
    # getter
    assert halo_exchange.halo_depth is None
    # setter
    halo_exchange.halo_depth = halo_depth
    assert halo_exchange.halo_depth == halo_depth


def test_haloexchange_vector_index_depend():
    '''check that _find_read_arguments does not return a haloexchange as a
    read dependence if the source node is a halo exchange and its
    field is a vector and the other halo exchange accesses a different
    element of the vector

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "4.9_named_multikernel_invokes.f90"),
                           api="dynamo0.3")
    psy = PSyFactory("dynamo0.3", distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    first_d_field_halo_exchange = schedule.children[3]
    field = first_d_field_halo_exchange.field
    all_nodes = schedule.walk(schedule.children, Node)
    following_nodes = all_nodes[4:]
    result_list = field._find_read_arguments(following_nodes)
    assert len(result_list) == 1
    assert result_list[0].call.name == 'ru_code'


def test_find_write_arguments_for_write():
    '''when backward_write_dependencies is called from an field argument
    that does not read then we should return an empty list. This test
    checks this functionality. We use the dynamo0p3 api to create the
    required objects

    '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "1_single_invoke.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    loop = schedule.children[3]
    kernel = loop.children[0]
    field_writer = kernel.arguments.args[1]
    node_list = field_writer.backward_write_dependencies()
    assert node_list == []


def test_find_w_args_hes_no_vec(monkeypatch, annexed):
    '''when backward_write_dependencies, or forward_read_dependencies, are
    called and a dependence is found between two halo exchanges, then
    the field must be a vector field. If the field is not a vector
    then an exception is raised. This test checks that the exception
    is raised correctly. Also test with and without annexed dofs being
    computed as this affects the generated code.

    '''
    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    if annexed:
        index = 4
    else:
        index = 5
    halo_exchange_d_v3 = schedule.children[index]
    field_d_v3 = halo_exchange_d_v3.field
    monkeypatch.setattr(field_d_v3, "_vector_size", 1)
    with pytest.raises(InternalError) as excinfo:
        _ = field_d_v3.backward_write_dependencies()
    assert ("DataAccess.overlaps(): vector sizes differ for field 'd' in two "
            "halo exchange calls. Found '1' and '3'" in str(excinfo.value))


def test_find_w_args_hes_diff_vec(monkeypatch, annexed):
    '''when backward_write_dependencies, or forward_read_dependencies, are
    called and a dependence is found between two halo exchanges, then
    the associated fields must be equal size vectors . If the fields
    are not vectors of equal size then an exception is raised. This
    test checks that the exception is raised correctly. Also test with
    and without annexed dofs being computed as this affects the
    generated code.

    '''
    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    if annexed:
        index = 4
    else:
        index = 5
    halo_exchange_d_v3 = schedule.children[index]
    field_d_v3 = halo_exchange_d_v3.field
    monkeypatch.setattr(field_d_v3, "_vector_size", 2)
    with pytest.raises(InternalError) as excinfo:
        _ = field_d_v3.backward_write_dependencies()
    assert ("DataAccess.overlaps(): vector sizes differ for field 'd' in two "
            "halo exchange calls. Found '2' and '3'" in str(excinfo.value))


def test_find_w_args_hes_vec_idx(monkeypatch, annexed):
    '''when backward_write_dependencies, or forward_read_dependencies are
    called, and a dependence is found between two halo exchanges, then
    the vector indices of the two halo exchanges must be different. If
    the vector indices have the same value then an exception is
    raised. This test checks that the exception is raised
    correctly. Also test with and without annexed dofs being computed
    as this affects the generated code.

    '''
    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    if annexed:
        index = 4
    else:
        index = 5
    halo_exchange_d_v3 = schedule.children[index]
    field_d_v3 = halo_exchange_d_v3.field
    halo_exchange_d_v2 = schedule.children[index-1]
    monkeypatch.setattr(halo_exchange_d_v2, "_vector_index", 3)
    with pytest.raises(InternalError) as excinfo:
        _ = field_d_v3.backward_write_dependencies()
    assert ("DataAccess:update_coverage() The halo exchange vector indices "
            "for 'd' are the same. This should never happen"
            in str(excinfo.value))


def test_find_w_args_hes_vec_no_dep():
    '''when _find_write_arguments, or _find_read_arguments, are called,
    halo exchanges with the same field but a different index should
    not depend on each other. This test checks that this behaviour is
    working correctly
    '''

    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    halo_exchange_d_v3 = schedule.children[5]
    field_d_v3 = halo_exchange_d_v3.field
    # there are two halo exchanges before d_v3 which should not count
    # as dependencies
    node_list = field_d_v3.backward_write_dependencies()
    assert node_list == []


def test_check_vect_hes_differ_wrong_argtype():
    '''when the check_vector_halos_differ method is called from a halo
    exchange object the argument being passed should be a halo
    exchange. If this is not the case an exception should be
    raised. This test checks that this exception is working correctly.
    '''

    _, invoke_info = parse(os.path.join(BASE_PATH, "1_single_invoke.f90"),
                           distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    halo_exchange = schedule.children[0]
    with pytest.raises(GenerationError) as excinfo:
        # pass an incorrect object to the method
        halo_exchange.check_vector_halos_differ(psy)
    assert (
        "the argument passed to HaloExchange.check_vector_halos_differ() "
        "is not a halo exchange object" in str(excinfo.value))


def test_check_vec_hes_differ_diff_names():
    '''when the check_vector_halos_differ method is called from a halo
    exchange object the argument being passed should be a halo
    exchange with an argument having the same name as the local halo
    exchange argument name. If this is not the case an exception
    should be raised. This test checks that this exception is working
    correctly.
    '''

    _, invoke_info = parse(os.path.join(BASE_PATH, "1_single_invoke.f90"),
                           distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    halo_exchange = schedule.children[0]
    # obtain another halo exchange object which has an argument with a
    # different name
    different_halo_exchange = schedule.children[1]
    with pytest.raises(GenerationError) as excinfo:
        # pass halo exchange with different name to the method
        halo_exchange.check_vector_halos_differ(different_halo_exchange)
    assert (
        "the halo exchange object passed to "
        "HaloExchange.check_vector_halos_differ() has a "
        "different field name 'm1' to self 'f2'" in str(excinfo.value))


def test_find_w_args_multiple_deps_error(monkeypatch, annexed):
    '''when _find_write_arguments finds a write that causes it to return
    there should not be any previous dependencies. This test checks
    that an error is raised if this is not the case. We test with
    annexed dofs is True and False as different numbers of halo
    exchanges are created.

    '''

    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)

    _, invoke_info = parse(
        os.path.join(BASE_PATH, "8.3_multikernel_invokes_vector.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # create halo exchanges between the two loops via redundant
    # computation
    if annexed:
        index = 1
    else:
        index = 4
    rc_trans = Dynamo0p3RedundantComputationTrans()
    rc_trans.apply(schedule.children[index], depth=2)
    del schedule.children[index]
    loop = schedule.children[index+2]
    kernel = loop.children[0]
    d_field = kernel.arguments.args[0]
    with pytest.raises(InternalError) as excinfo:
        d_field.backward_write_dependencies()
    assert (
        "Found a writer dependence but there are already dependencies"
        in str(excinfo.value))


def test_find_write_arguments_no_more_nodes(monkeypatch, annexed):
    '''when _find_write_arguments has looked through all nodes but has not
    returned it should mean that is has not found any write
    dependencies. This test checks that an error is raised if this is
    not the case. We test with and without computing annexed dofs as
    different numbers of halo exchanges are created.

    '''

    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)

    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    if annexed:
        index = 3
    else:
        index = 4
    del schedule.children[index]
    loop = schedule.children[index+1]
    kernel = loop.children[0]
    d_field = kernel.arguments.args[5]
    with pytest.raises(InternalError) as excinfo:
        d_field.backward_write_dependencies()
    assert (
        "no more nodes but there are already dependencies"
        in str(excinfo.value))


def test_find_w_args_multiple_deps(monkeypatch, annexed):
    '''_find_write_arguments should return as many halo exchange
    dependencies as the vector size of the associated field. This test
    checks that this is the case and that the returned objects are
    what is expected. We test with annexed dofs is True and False as
    different numbers of halo exchanges are created.

    '''

    config = Config.get()
    dyn_config = config.api_conf("dynamo0.3")
    monkeypatch.setattr(dyn_config, "_compute_annexed_dofs", annexed)

    _, invoke_info = parse(
        os.path.join(BASE_PATH, "8.3_multikernel_invokes_vector.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # create halo exchanges between the two loops via redundant
    # computation
    if annexed:
        index = 1
    else:
        index = 4
    rc_trans = Dynamo0p3RedundantComputationTrans()
    rc_trans.apply(schedule.children[index], depth=2)
    loop = schedule.children[index+3]
    kernel = loop.children[0]
    d_field = kernel.arguments.args[0]
    vector_size = d_field.vector_size
    result_list = d_field.backward_write_dependencies()
    # we have as many dependencies as the field vector size
    assert vector_size == len(result_list)
    indices = set()
    for result in result_list:
        # each dependence is a halo exchange nodes
        assert isinstance(result.call, HaloExchange)
        # the name of the halo exchange field and the initial
        # field are the same
        assert result.name == d_field.name
        # the size of the halo exchange field vector and the initial
        # field vector are the same
        assert result.vector_size == vector_size
        indices.add(result.call.vector_index)
    # each of the indices are unique (otherwise the set would be
    # smaller)
    assert len(indices) == vector_size


def test_loop_props():
    ''' Tests for the properties of a Loop object. '''
    from psyclone.psyGen import Loop
    _, invoke = get_invoke("single_invoke.f90", "gocean1.0", idx=0)
    sched = invoke.schedule
    loop = sched.children[0].children[0]
    assert isinstance(loop, Loop)
    with pytest.raises(GenerationError) as err:
        loop.loop_type = "not_a_valid_type"
    assert ("loop_type value (not_a_valid_type) is invalid. Must be one of "
            "['inner', 'outer']" in str(err))


def test_node_abstract_methods():
    ''' Tests that the abstract methods of the Node class raise appropriate
    errors. '''
    from psyclone.psyGen import Node
    _, invoke = get_invoke("single_invoke.f90", "gocean1.0", idx=0)
    sched = invoke.schedule
    loop = sched.children[0].children[0]
    with pytest.raises(NotImplementedError) as err:
        Node.gen_code(loop)
    assert ("Please implement me" in str(err))
    with pytest.raises(NotImplementedError) as err:
        Node.view(loop)
    assert ("BaseClass of a Node must implement the view method" in str(err))


def test_kern_ast():
    ''' Test that we can obtain the fparser2 AST of a kernel. '''
    from psyclone.gocean1p0 import GOKern
    from fparser.two import Fortran2003
    _, invoke = get_invoke("nemolite2d_alg_mod.f90", "gocean1.0", idx=0)
    sched = invoke.schedule
    kern = sched.children[0].children[0].children[0]
    assert isinstance(kern, GOKern)
    assert kern.ast
    assert isinstance(kern.ast, Fortran2003.Program)


def test_dataaccess_vector():
    '''Test that the DataAccess class works as expected when we have a
    vector field argument that depends on more than one halo exchange
    (due to halo exchanges working separately on components of
    vectors).

    '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule

    # d from halo exchange vector 1
    halo_exchange_d_v1 = schedule.children[3]
    field_d_v1 = halo_exchange_d_v1.field
    # d from halo exchange vector 2
    halo_exchange_d_v2 = schedule.children[4]
    field_d_v2 = halo_exchange_d_v2.field
    # d from halo exchange vector 3
    halo_exchange_d_v3 = schedule.children[5]
    field_d_v3 = halo_exchange_d_v3.field
    # d from a kernel argument
    loop = schedule.children[6]
    kernel = loop.children[0]
    d_arg = kernel.arguments.args[5]

    access = DataAccess(d_arg)
    assert not access.covered

    access.update_coverage(field_d_v3)
    assert not access.covered
    access.update_coverage(field_d_v2)
    assert not access.covered

    with pytest.raises(InternalError) as excinfo:
        access.update_coverage(field_d_v3)
    assert (
        "Found more than one dependent halo exchange with the same vector "
        "index" in str(excinfo.value))

    access.update_coverage(field_d_v1)
    assert access.covered

    access.reset_coverage()
    assert not access.covered
    assert not access._vector_index_access


def test_dataaccess_same_vector_indices(monkeypatch):
    '''If update_coverage() is called from DataAccess and the arguments
    are the same vector field, and the field vector indices are the
    same then check that an exception is raised. This particular
    exception is difficult to raise as it is caught by an earlier
    method (overlaps()).

    '''
    _, invoke_info = parse(
        os.path.join(BASE_PATH, "4.9_named_multikernel_invokes.f90"),
        distributed_memory=True, api="dynamo0.3")
    psy = PSyFactory("dynamo0.3",
                     distributed_memory=True).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    # d for this halo exchange is for vector component 2
    halo_exchange_d_v2 = schedule.children[4]
    field_d_v2 = halo_exchange_d_v2.field
    # modify d from vector component 3 to be component 2
    halo_exchange_d_v3 = schedule.children[5]
    field_d_v3 = halo_exchange_d_v3.field
    monkeypatch.setattr(halo_exchange_d_v3, "_vector_index", 2)

    # Now raise an exception with our erroneous vector indices (which
    # are the same but should not be), but first make sure that the
    # overlaps() method returns True otherwise an earlier exception
    # will be raised.
    access = DataAccess(field_d_v2)
    monkeypatch.setattr(access, "overlaps", lambda arg: True)

    with pytest.raises(InternalError) as excinfo:
        access.update_coverage(field_d_v3)
    assert (
        "The halo exchange vector indices for 'd' are the same. This should "
        "never happen" in str(excinfo.value))


# Test CodeBlock class


def test_codeblock_view(capsys):
    ''' Check the view and colored_text methods of the Code Block class.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    cblock = CodeBlock([])
    coloredtext = colored("CodeBlock", SCHEDULE_COLOUR_MAP["CodeBlock"])
    cblock.view()
    output, _ = capsys.readouterr()
    assert coloredtext+"[" in output
    assert "]" in output


def test_codeblock_can_be_printed():
    '''Test that an CodeBlck instance can always be printed (i.e. is
    initialised fully)'''
    cblock = CodeBlock([])
    assert "CodeBlock[" in str(cblock)
    assert "]" in str(cblock)

# Test Assignment class


def test_assignment_view(capsys):
    ''' Check the view and colored_text methods of the Assignment class.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP

    assignment = Assignment()
    coloredtext = colored("Assignment", SCHEDULE_COLOUR_MAP["Assignment"])
    assignment.view()
    output, _ = capsys.readouterr()
    assert coloredtext+"[]" in output


def test_assignment_can_be_printed():
    '''Test that an Assignment instance can always be printed (i.e. is
    initialised fully)'''
    assignment = Assignment()
    assert "Assignment[]\n" in str(assignment)


# Test Reference class


def test_reference_view(capsys):
    ''' Check the view and colored_text methods of the Reference class.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    kschedule = KernelSchedule("kname")
    kschedule.symbol_table.declare("rname", "integer")
    assignment = Assignment(parent=kschedule)
    ref = Reference("rname", assignment)
    coloredtext = colored("Reference", SCHEDULE_COLOUR_MAP["Reference"])
    ref.view()
    output, _ = capsys.readouterr()
    assert coloredtext+"[name:'rname']" in output


def test_reference_can_be_printed():
    '''Test that a Reference instance can always be printed (i.e. is
    initialised fully)'''
    kschedule = KernelSchedule("kname")
    kschedule.symbol_table.declare("rname", "integer")
    assignment = Assignment(parent=kschedule)
    ref = Reference("rname", assignment)
    assert "Reference[name:'rname']\n" in str(ref)


# Test Array class


def test_array_view(capsys):
    ''' Check the view and colored_text methods of the Array class.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    kschedule = KernelSchedule("kname")
    kschedule.symbol_table.declare("aname", "integer", [None])
    assignment = Assignment(parent=kschedule)
    array = Array("aname", parent=assignment)
    coloredtext = colored("ArrayReference", SCHEDULE_COLOUR_MAP["Reference"])
    array.view()
    output, _ = capsys.readouterr()
    assert coloredtext+"[name:'aname']" in output


def test_array_can_be_printed():
    '''Test that an Array instance can always be printed (i.e. is
    initialised fully)'''
    kschedule = KernelSchedule("kname")
    kschedule.symbol_table.declare("aname", "integer")
    assignment = Assignment(parent=kschedule)
    array = Array("aname", assignment)
    assert "ArrayReference[name:'aname']\n" in str(array)


# Test Literal class


def test_literal_view(capsys):
    ''' Check the view and colored_text methods of the Literal class.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    literal = Literal("1")
    coloredtext = colored("Literal", SCHEDULE_COLOUR_MAP["Literal"])
    literal.view()
    output, _ = capsys.readouterr()
    assert coloredtext+"[value:'1']" in output


def test_literal_can_be_printed():
    '''Test that an Literal instance can always be printed (i.e. is
    initialised fully)'''
    literal = Literal("1")
    assert "Literal[value:'1']\n" in str(literal)


# Test BinaryOperation class

def test_binaryoperation_view(capsys):
    ''' Check the view and colored_text methods of the Binary Operation
    class.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    binaryOp = BinaryOperation("+")
    op1 = Literal("1", parent=binaryOp)
    op2 = Literal("1", parent=binaryOp)
    binaryOp.addchild(op1)
    binaryOp.addchild(op2)
    coloredtext = colored("BinaryOperation",
                          SCHEDULE_COLOUR_MAP["BinaryOperation"])
    binaryOp.view()
    output, _ = capsys.readouterr()
    assert coloredtext+"[operator:'+']" in output


def test_binaryoperation_can_be_printed():
    '''Test that a Binary Operation instance can always be printed (i.e. is
    initialised fully)'''
    binaryOp = BinaryOperation("+")
    op1 = Literal("1", parent=binaryOp)
    op2 = Literal("1", parent=binaryOp)
    binaryOp.addchild(op1)
    binaryOp.addchild(op2)
    assert "BinaryOperation[operator:'+']\n" in str(binaryOp)


# Test KernelSchedule Class

def test_kernelschedule_view(capsys):
    '''Test the view method of the KernelSchedule part.'''
    from psyclone.psyGen import colored, SCHEDULE_COLOUR_MAP
    kschedule = KernelSchedule("kname")
    kschedule.symbol_table.declare("x", "integer")
    assignment = Assignment()
    kschedule.addchild(assignment)
    lhs = Reference("x", parent=assignment)
    rhs = Literal("1", parent=assignment)
    assignment.addchild(lhs)
    assignment.addchild(rhs)
    kschedule.view()
    coloredtext = colored("Schedule",
                          SCHEDULE_COLOUR_MAP["Schedule"])
    output, _ = capsys.readouterr()
    assert coloredtext+"[name:'kname']" in output
    assert "Assignment" in output  # Check child view method is called


def test_kernelschedule_can_be_printed():
    '''Test that a KernelSchedule instance can always be printed (i.e. is
    initialised fully)'''
    kschedule = KernelSchedule("kname")
    kschedule.symbol_table.declare("x", "integer")
    assignment = Assignment()
    kschedule.addchild(assignment)
    lhs = Reference("x", parent=assignment)
    rhs = Literal("1", parent=assignment)
    assignment.addchild(lhs)
    assignment.addchild(rhs)
    assert "Schedule[name:'kname']:\n" in str(kschedule)
    assert "Assignment" in str(kschedule)  # Check children are printed
    assert "End Schedule" in str(kschedule)


# Test Symbol Class
def test_symbol_initialization():
    '''Test that a Symbol instance can be created when valid arguments are
    given, otherwise raise relevant exceptions.'''

    # Test with valid arguments
    assert isinstance(Symbol('a', 'real'), Symbol)
    assert isinstance(Symbol('a', 'integer'), Symbol)
    assert isinstance(Symbol('a', 'character'), Symbol)
    assert isinstance(Symbol('a', 'real', [None]), Symbol)
    assert isinstance(Symbol('a', 'real', [3]), Symbol)
    assert isinstance(Symbol('a', 'real', [3, None]), Symbol)
    assert isinstance(Symbol('a', 'real', [], 'local'), Symbol)
    assert isinstance(Symbol('a', 'real', [], 'global_argument'), Symbol)
    assert isinstance(Symbol('a', 'real', [], 'global_argument',
                             True, True), Symbol)
    assert isinstance(Symbol('a', 'real', [], 'global_argument',
                             True, False), Symbol)

    # Test with invalid arguments
    with pytest.raises(NotImplementedError) as error:
        Symbol('a', 'invalidtype', [], 'local')
    assert ("Symbol can only be initialized with {0} datatypes."
            "".format(str(Symbol.valid_data_types)))in str(error.value)

    with pytest.raises(ValueError) as error:
        Symbol('a', 'real', [], 'invalidscope')
    assert ("Symbol scope attribute can only be one of " +
            str(Symbol.valid_scope_types) +
            " but got 'invalidscope'.") in str(error.value)

    with pytest.raises(TypeError) as error:
        Symbol('a', 'real', None, 'local')
    assert "Symbol shape attribute must be a list." in str(error.value)

    with pytest.raises(TypeError) as error:
        Symbol('a', 'real', ['invalidshape'], 'local')
    assert ("Symbol shape list elements can only be "
            "'integer' or 'None'.") in str(error.value)


def test_symbol_scope_setter():
    '''Test that a Symbol scope can be set if given a new valid scope
    value, otherwise it raises a relevant exception'''

    # Test with valid scope value
    sym = Symbol('a', 'real', [], 'local')
    assert sym.scope == 'local'
    sym.scope = 'global_argument'
    assert sym.scope == 'global_argument'

    # Test with invalid scope value
    with pytest.raises(ValueError) as error:
        sym.scope = 'invalidscope'
    assert ("Symbol scope attribute can only be one of " +
            str(Symbol.valid_scope_types) +
            " but got 'invalidscope'.") in str(error.value)


def test_symbol_is_input_setter():
    '''Test that a Symbol is_input can be set if given a new valid
    value, otherwise it raises a relevant exception'''

    sym = Symbol('a', 'real', [], 'global_argument', False, False)
    sym.is_input = True
    assert sym.is_input is True

    with pytest.raises(TypeError) as error:
        sym.is_input = 3
    assert "Symbol 'is_input' attribute must be a boolean." in \
           str(error.value)

    sym = Symbol('a', 'real', [], 'local')
    with pytest.raises(ValueError) as error:
        sym.is_input = True
    assert ("Symbol with 'local' scope can not have 'is_input' attribute"
            " set to True.") in str(error.value)


def test_symbol_is_output_setter():
    '''Test that a Symbol is_output can be set if given a new valid
    value, otherwise it raises a relevant exception'''
    sym = Symbol('a', 'real', [], 'global_argument', False, False)
    sym.is_output = True
    assert sym.is_output is True

    with pytest.raises(TypeError) as error:
        sym.is_output = 3
    assert "Symbol 'is_output' attribute must be a boolean." in \
           str(error.value)

    sym = Symbol('a', 'real', [], 'local')
    with pytest.raises(ValueError) as error:
        sym.is_output = True
    assert ("Symbol with 'local' scope can not have 'is_output' attribute"
            " set to True.") in str(error.value)


def test_symbol_can_be_printed():
    '''Test that a Symbol instance can always be printed. (i.e. is
    initialised fully)'''
    symbol = Symbol("sname", "real")
    assert "sname<real, [], local>" in str(symbol)


# Test SymbolTable Class

def test_symboltable_declare():
    '''Test that the declare method inserts new symbols in the symbol
    table, but raises appropiate errors when provied with wrong parameters
    or duplicate declarations.'''
    sym_table = SymbolTable()

    # Declare a symbol
    sym_table.declare("var1", "real", [5, 1], "global_argument", True, True)
    assert sym_table._symbols["var1"].name == "var1"
    assert sym_table._symbols["var1"].datatype == "real"
    assert sym_table._symbols["var1"].shape == [5, 1]
    assert sym_table._symbols["var1"].scope == "global_argument"
    assert sym_table._symbols["var1"].is_input is True
    assert sym_table._symbols["var1"].is_output is True

    # Declare a duplicate name symbol
    with pytest.raises(KeyError) as error:
        sym_table.declare("var1", "real")
    assert ("Symbol table already contains a symbol with name "
            "'var1'.") in str(error.value)


def test_symboltable_lookup():
    '''Test that the lookup method retrives symbols from the symbol table
    if the name exists, otherwise it raises an error.'''
    sym_table = SymbolTable()
    sym_table.declare("var1", "real", [None, None])
    sym_table.declare("var2", "integer", [])
    sym_table.declare("var3", "real", [])

    assert isinstance(sym_table.lookup("var1"), Symbol)
    assert sym_table.lookup("var1").name == "var1"
    assert isinstance(sym_table.lookup("var2"), Symbol)
    assert sym_table.lookup("var2").name == "var2"
    assert isinstance(sym_table.lookup("var3"), Symbol)
    assert sym_table.lookup("var3").name == "var3"

    with pytest.raises(KeyError) as error:
        sym_table.lookup("notdeclared")
    assert "Could not find 'notdeclared' in the Symbol Table." in \
        str(error.value)


def test_symboltable_view(capsys):
    '''Test the view method of the SymbolTable class, it should print to
    standard out a representation of the full SymbolTable.'''
    sym_table = SymbolTable()
    sym_table.declare("var1", "real")
    sym_table.declare("var2", "integer")
    sym_table.view()
    output, _ = capsys.readouterr()
    assert "Symbol Table:\n" in output
    assert "var1" in output
    assert "var2" in output


def test_symboltable_can_be_printed():
    '''Test that a SymbolTable instance can always be printed. (i.e. is
    initialised fully)'''
    sym_table = SymbolTable()
    sym_table.declare("var1", "real")
    sym_table.declare("var2", "integer")
    assert "Symbol Table:\n" in str(sym_table)
    assert "var1" in str(sym_table)
    assert "var2" in str(sym_table)


# Test Fparser2ASTProcessor

def test_fparser2astprocessor_generate_schedule_empty_subroutine():
    ''' Tests the fparser2AST generate_schedule method with an empty
    subroutine.
    '''
    ast1 = fpapi.parse(FAKE_KERNEL_METADATA, ignore_comments=True)
    metadata = DynKernMetadata(ast1)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    ast2 = my_kern.ast
    processor = Fparser2ASTProcessor()

    # Test properly formed but empty kernel module
    schedule = processor.generate_schedule("dummy_code", ast2)
    assert isinstance(schedule, KernelSchedule)

    # Test that we get an error for a nonexistant subroutine name
    with pytest.raises(GenerationError) as error:
        schedule = processor.generate_schedule("nonexistent_code", ast2)
    assert "Unexpected kernel AST. Could not find " \
           "subroutine: nonexistent_code" in str(error.value)

    # Test corrupting ast by deleting subroutine
    del ast2.content[0].content[2]
    with pytest.raises(GenerationError) as error:
        schedule = processor.generate_schedule("dummy_code", ast2)
    assert "Unexpected kernel AST. Could not find " \
           "subroutine: dummy_code" in str(error.value)


def test_fparser2astprocessor_generate_schedule_two_modules():
    ''' Tests the fparser2AST generate_schedule method raises an exception
    when more than one fparser2 module node is provided.
    '''
    ast1 = fpapi.parse(FAKE_KERNEL_METADATA*2, ignore_comments=True)
    metadata = DynKernMetadata(ast1)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    ast2 = my_kern.ast
    processor = Fparser2ASTProcessor()

    # Test kernel with two modules
    with pytest.raises(GenerationError) as error:
        _ = processor.generate_schedule("dummy_code", ast2)
    assert ("Unexpected AST when generating 'dummy_code' kernel schedule."
            " Just one module definition per file supported.") \
        in str(error.value)


def test_fparser2astprocessor_generate_schedule_dummy_subroutine():
    ''' Tests the fparser2AST generate_schedule method with a simple
    subroutine.
    '''
    dummy_kernel_metadata = '''
    module dummy_mod
      type, extends(kernel_type) :: dummy_type
         type(arg_type), meta_args(3) =                    &
              (/ arg_type(gh_field, gh_write,     w3),     &
                 arg_type(gh_field, gh_readwrite, wtheta), &
                 arg_type(gh_field, gh_inc,       w1)      &
               /)
         integer :: iterates_over = cells
       contains
         procedure, nopass :: code => dummy_code
      end type dummy_type
    contains
     subroutine dummy_code(f1, f2, f3)
        real(wp), dimension(:,:), intent(in)  :: f1
        real(wp), dimension(:,:), intent(out)  :: f2
        real(wp), dimension(:,:) :: f3
        f2 = f1 + 1
      end subroutine dummy_code
    end module dummy_mod
    '''
    ast1 = fpapi.parse(dummy_kernel_metadata, ignore_comments=True)
    metadata = DynKernMetadata(ast1)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    ast2 = my_kern.ast
    processor = Fparser2ASTProcessor()

    # Test properly formed kernel module
    schedule = processor.generate_schedule("dummy_code", ast2)
    assert isinstance(schedule, KernelSchedule)

    # Test argument intent is inferred when not available in the declaration
    assert schedule.symbol_table.lookup('f3').scope == 'global_argument'
    assert schedule.symbol_table.lookup('f3').is_input is True
    assert schedule.symbol_table.lookup('f3').is_output is True

    # Test that a kernel subroutine without Execution_Part still creates a
    # valid KernelSchedule
    del ast2.content[0].content[2].content[1].content[2]
    schedule = processor.generate_schedule("dummy_code", ast2)
    assert isinstance(schedule, KernelSchedule)
    assert not schedule.children


def test_fparser2astprocessor_generate_schedule_no_args_subroutine():
    ''' Tests the fparser2AST generate_schedule method with a simple
    subroutine with no arguments.
    '''
    dummy_kernel_metadata = '''
    module dummy_mod
      type, extends(kernel_type) :: dummy_type
        type(arg_type), meta_args(3) =                    &
              (/ arg_type(gh_field, gh_write,     w3),     &
                 arg_type(gh_field, gh_readwrite, wtheta), &
                 arg_type(gh_field, gh_inc,       w1)      &
               /)
         integer :: iterates_over = cells
       contains
         procedure, nopass :: code => dummy_code
      end type dummy_type
    contains
     subroutine dummy_code()
        real(wp), dimension(:,:) :: f3
        f3 = f3 + 1
      end subroutine dummy_code
    end module dummy_mod
    '''
    ast1 = fpapi.parse(dummy_kernel_metadata, ignore_comments=True)
    metadata = DynKernMetadata(ast1)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    ast2 = my_kern.ast
    processor = Fparser2ASTProcessor()

    # Test kernel with no arguments, should still proceed
    schedule = processor.generate_schedule("dummy_code", ast2)
    assert isinstance(schedule, KernelSchedule)
    # TODO: In the future we could validate that metadata matches
    # the kernel arguments, then this test would fail. Issue #288


def test_fparser2astprocessor_generate_schedule_unmatching_arguments():
    ''' Tests the fparser2AST generate_schedule with unmatching kernel
    arguments and declarations raises the appropriate exception.
    '''
    dummy_kernel_metadata = '''
    module dummy_mod
      type, extends(kernel_type) :: dummy_type
         type(arg_type), meta_args(3) =                    &
              (/ arg_type(gh_field, gh_write,     w3),     &
                 arg_type(gh_field, gh_readwrite, wtheta), &
                 arg_type(gh_field, gh_inc,       w1)      &
               /)
         integer :: iterates_over = cells
       contains
         procedure, nopass :: code => dummy_code
      end type dummy_type
    contains
     subroutine dummy_code(f1, f2, f3, f4)
        real(wp), dimension(:,:), intent(in)  :: f1
        real(wp), dimension(:,:), intent(out)  :: f2
        real(wp), dimension(:,:) :: f3
        f2 = f1 + 1
      end subroutine dummy_code
    end module dummy_mod
    '''
    ast1 = fpapi.parse(dummy_kernel_metadata, ignore_comments=True)
    metadata = DynKernMetadata(ast1)
    my_kern = DynKern()
    my_kern.load_meta(metadata)
    ast2 = my_kern.ast
    processor = Fparser2ASTProcessor()

    # Test exception for unmatching argument list
    with pytest.raises(InternalError) as error:
        _ = processor.generate_schedule("dummy_code", ast2)
    assert "The kernel argument list" in str(error.value)
    assert "does not match the variable declarations for fparser nodes" \
        in str(error.value)


def test_fparser2astprocessor_process_declarations(f2008_parser):
    '''Test that process_declarations method of fparse2astprocessor
    converts the fparser2 declarations to symbols in the provided
    parent Kernel Schedule.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Specification_Part
    fake_parent = KernelSchedule("dummy_schedule")
    processor = Fparser2ASTProcessor()

    # Test simple declarations
    reader = FortranStringReader("integer :: l1")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("l1").name == 'l1'
    assert fake_parent.symbol_table.lookup("l1").datatype == 'integer'
    assert fake_parent.symbol_table.lookup("l1").shape == []
    assert fake_parent.symbol_table.lookup("l1").scope == 'local'
    assert fake_parent.symbol_table.lookup("l1").is_input is False
    assert fake_parent.symbol_table.lookup("l1").is_output is False

    reader = FortranStringReader("Real      ::      l2")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("l2").name == "l2"
    assert fake_parent.symbol_table.lookup("l2").datatype == 'real'

    # Test with unsupported data type
    reader = FortranStringReader("logical      ::      c2")
    fparser2spec = Specification_Part(reader).content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert "Could not process " in str(error.value)
    assert (". Only 'real', 'integer' and 'character' intrinsic types are"
            " supported.") in str(error.value)

    # Test with unsupported attribute
    reader = FortranStringReader("real, public :: p2")
    fparser2spec = Specification_Part(reader).content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert "Could not process " in str(error.value)
    assert "Unrecognized attribute type " in str(error.value)

    # RHS array specifications are not supported
    reader = FortranStringReader("integer :: l1(4)")
    fparser2spec = Specification_Part(reader).content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert ("Array specifications after the variable name are not "
            "supported.") in str(error.value)

    # Initialisations are not supported
    reader = FortranStringReader("integer :: l1 = 1")
    fparser2spec = Specification_Part(reader).content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert ("Initializations on the declaration statements are not "
            "supported.") in str(error.value)

    # Char lengths are not supported
    # TODO: It would be simpler to do just a Specification_Part(reader) instead
    # of parsing a full program, but fparser/169 needs to be fixed first.
    reader = FortranStringReader("program dummy\ncharacter :: l*4"
                                 "\nend program")
    program = f2008_parser(reader)
    fparser2spec = program.content[0].content[1].content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert ("Character length specifications are not "
            "supported.") in str(error.value)


def test_fparser2astprocessor_process_not_supported_declarations(f2008_parser):
    '''Test that process_declarations method raises the proper errors when
    declarations contain unsupported attributes.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Specification_Part
    fake_parent = KernelSchedule("dummy_schedule")
    processor = Fparser2ASTProcessor()

    reader = FortranStringReader("integer, external :: arg1")
    fparser2spec = Specification_Part(reader).content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert "Could not process " in str(error.value)
    assert ". Unrecognized attribute " in str(error.value)

    reader = FortranStringReader("integer, save :: arg1")
    fparser2spec = Specification_Part(reader).content[0]
    with pytest.raises(NotImplementedError) as error:
        processor.process_declarations(fake_parent, [fparser2spec], [])
    assert "Could not process " in str(error.value)
    assert ". Unrecognized attribute " in str(error.value)


def test_fparser2astprocessor_process_declarations_intent(f2008_parser):
    '''Test that process_declarations method handles various different
    specifications of variable attributes.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Specification_Part
    fake_parent = KernelSchedule("dummy_schedule")
    processor = Fparser2ASTProcessor()

    reader = FortranStringReader("integer, intent(in) :: arg1")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("arg1").scope == 'global_argument'
    assert fake_parent.symbol_table.lookup("arg1").is_input is True
    assert fake_parent.symbol_table.lookup("arg1").is_output is False

    reader = FortranStringReader("integer, intent( IN ) :: arg2")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("arg2").scope == 'global_argument'
    assert fake_parent.symbol_table.lookup("arg2").is_input is True
    assert fake_parent.symbol_table.lookup("arg2").is_output is False

    reader = FortranStringReader("integer, intent( Out ) :: arg3")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("arg3").scope == 'global_argument'
    assert fake_parent.symbol_table.lookup("arg3").is_input is False
    assert fake_parent.symbol_table.lookup("arg3").is_output is True

    reader = FortranStringReader("integer, intent ( InOut ) :: arg4")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("arg4").scope == 'global_argument'
    assert fake_parent.symbol_table.lookup("arg4").is_input is True
    assert fake_parent.symbol_table.lookup("arg4").is_output is True


def test_fparser2astprocessor_parse_array_dimensions_attributes(
        f2008_parser):
    '''Test that process_declarations method parses multiple specifications
    of array attributes.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Specification_Part
    from fparser.two.Fortran2003 import Dimension_Attr_Spec

    reader = FortranStringReader("dimension(:)")
    fparser2spec = Dimension_Attr_Spec(reader)
    shape = Fparser2ASTProcessor._parse_dimensions(fparser2spec)
    assert shape == [None]

    reader = FortranStringReader("dimension(:,:,:)")
    fparser2spec = Dimension_Attr_Spec(reader)
    shape = Fparser2ASTProcessor._parse_dimensions(fparser2spec)
    assert shape == [None, None, None]

    reader = FortranStringReader("dimension(3,5)")
    fparser2spec = Dimension_Attr_Spec(reader)
    shape = Fparser2ASTProcessor._parse_dimensions(fparser2spec)
    assert shape == [3, 5]

    reader = FortranStringReader("dimension(*)")
    fparser2spec = Dimension_Attr_Spec(reader)
    with pytest.raises(NotImplementedError) as error:
        _ = Fparser2ASTProcessor._parse_dimensions(fparser2spec)
    assert "Could not process " in str(error.value)
    assert "Assumed-size arrays are not supported." in str(error.value)

    reader = FortranStringReader("dimension(var1)")
    fparser2spec = Dimension_Attr_Spec(reader)
    with pytest.raises(NotImplementedError) as error:
        _ = Fparser2ASTProcessor._parse_dimensions(fparser2spec)
    assert "Could not process " in str(error.value)
    assert ("Only integer literals are supported for explicit shape array"
            " declarations.") in str(error.value)

    # Test dimension and intent arguments together
    fake_parent = KernelSchedule("dummy_schedule")
    processor = Fparser2ASTProcessor()
    reader = FortranStringReader("real, intent(in), dimension(:) :: array3")
    fparser2spec = Specification_Part(reader).content[0]
    processor.process_declarations(fake_parent, [fparser2spec], [])
    assert fake_parent.symbol_table.lookup("array3").name == "array3"
    assert fake_parent.symbol_table.lookup("array3").datatype == 'real'
    assert fake_parent.symbol_table.lookup("array3").shape == [None]
    assert fake_parent.symbol_table.lookup("array3").scope == "global_argument"
    assert fake_parent.symbol_table.lookup("array3").is_input is True


def test_fparser2astprocessor_parse_array_dimensions_unhandled(
        f2008_parser, monkeypatch):
    '''Test that process_declarations method parses multiple specifications
    of array attributes.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Dimension_Attr_Spec
    import fparser

    def walk_ast_return(arg1, arg2):
        '''Function that returns a unique object that will not be part
        of the implemented handling in the walk_ast method caller.'''
        class invalid(object):
            pass
        newobject = invalid()
        return [newobject]

    monkeypatch.setattr(fparser.two.utils, 'walk_ast', walk_ast_return)

    reader = FortranStringReader("dimension(:)")
    fparser2spec = Dimension_Attr_Spec(reader)
    with pytest.raises(InternalError) as error:
        shape = Fparser2ASTProcessor._parse_dimensions(fparser2spec)
    assert "Reached end of loop body and" in str(error.value)
    assert " has not been handled." in str(error.value)


def test_fparser2astprocessor_handling_assignment_stmt(f2008_parser):
    ''' Test that fparser2 Assignment_Stmt is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("x=1")
    fparser2assignment = Execution_Part.match(reader)[0][0]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2assignment], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, Assignment)
    assert len(new_node.children) == 2


def test_fparser2astprocessor_handling_name(f2008_parser):
    ''' Test that fparser2 Name is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("x=1")
    fparser2name = Execution_Part.match(reader)[0][0].items[0]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2name], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, Reference)
    assert new_node._reference == "x"


def test_fparser2astprocessor_handling_parenthesis(f2008_parser):
    ''' Test that fparser2 Parenthesis is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("x=(x+1)")
    fparser2parenthesis = Execution_Part.match(reader)[0][0].items[2]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2parenthesis], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    # Check parenthesis are ignored and process_nodes uses its child
    assert isinstance(new_node, BinaryOperation)


def test_fparser2astprocessor_handling_part_ref(f2008_parser):
    ''' Test that fparser2 Part_Ref is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("x(i)=1")
    fparser2part_ref = Execution_Part.match(reader)[0][0].items[0]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2part_ref], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, Array)
    assert new_node._reference == "x"
    assert len(new_node.children) == 1  # Array dimensions

    reader = FortranStringReader("x(i+3,j-4,(z*5)+1)=1")
    fparser2part_ref = Execution_Part.match(reader)[0][0].items[0]

    fake_parent = Node()
    processor.process_nodes(fake_parent, [fparser2part_ref], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, Array)
    assert new_node._reference == "x"
    assert len(new_node.children) == 3  # Array dimensions


def test_fparser2astprocessor_handling_if_stmt(f2008_parser):
    ''' Test that fparser2 If_Stmt is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("if(x==1)y=1")
    fparser2if_stmt = Execution_Part.match(reader)[0][0]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2if_stmt], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, IfBlock)
    assert len(new_node.children) == 2


def test_fparser2astprocessor_handling_numberbase(f2008_parser):
    ''' Test that fparser2 NumberBase is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("x=1")
    fparser2number = Execution_Part.match(reader)[0][0].items[2]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2number], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, Literal)
    assert new_node._value == "1"


def test_fparser2astprocessor_handling_binaryopbase(f2008_parser):
    ''' Test that fparser2 BinaryOpBase is converted to expected PSyIR
    tree structure.
    '''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader("x=1+4")
    fparser2binaryOp = Execution_Part.match(reader)[0][0].items[2]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2binaryOp], None)
    # Check a new node was generated and connected to parent
    assert len(fake_parent.children) == 1
    new_node = fake_parent.children[0]
    assert isinstance(new_node, BinaryOperation)
    assert len(new_node.children) == 2
    assert new_node._operator == '+'


def test_fparser2astprocessor_handling_end_do_stmt(f2008_parser):
    ''' Test that fparser2 End_Do_Stmt are ignored.'''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Execution_Part
    reader = FortranStringReader('''
        do i=1,10
            a=a+1
        end do
        ''')
    fparser2enddo = Execution_Part.match(reader)[0][0].content[-1]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2enddo], None)
    assert len(fake_parent.children) == 0  # No new children created


def test_fparser2astprocessor_handling_end_subroutine_stmt(f2008_parser):
    ''' Test that fparser2 End_Subroutine_Stmt are ignored.'''
    from fparser.common.readfortran import FortranStringReader
    from fparser.two.Fortran2003 import Subroutine_Subprogram
    reader = FortranStringReader('''
        subroutine dummy_code()
        end subroutine dummy_code
        ''')
    fparser2endsub = Subroutine_Subprogram.match(reader)[0][-1]

    fake_parent = Node()
    processor = Fparser2ASTProcessor()
    processor.process_nodes(fake_parent, [fparser2endsub], None)
    assert len(fake_parent.children) == 0  # No new children created
