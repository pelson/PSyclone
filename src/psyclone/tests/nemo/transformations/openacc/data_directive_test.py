# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2018-2019, Science and Technology Facilities Council.
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
# Authors: R. W. Ford and A. R. Porter, STFC Daresbury Lab

'''Module containing py.test tests for the transformation of the PSy
   representation of NEMO code using the OpenACC data directive.

'''

from __future__ import print_function, absolute_import
import os
import pytest
from fparser.common.readfortran import FortranStringReader
from psyclone.parse import parse
from psyclone.psyGen import PSyFactory, TransInfo
from psyclone.transformations import TransformationError


# Constants
API = "nemo"
# Location of the Fortran files associated with these tests
BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "../../test_files")


def test_explicit():
    '''
    Check code generation for enclosing a single explicit loop containing a
    kernel inside a data region.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "explicit_do.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('explicit_do').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("  REAL, DIMENSION(jpi, jpj, jpk) :: umask\n"
            "  !$ACC DATA COPYOUT(umask)\n"
            "  DO jk = 1, jpk") in gen_code

    assert ("  END DO\n"
            "  !$ACC END DATA\n"
            "END PROGRAM explicit_do") in gen_code


def test_data_view(capsys):
    ''' Check that the ACCDataDirective.view() method works as expected. '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "explicit_do.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('explicit_do').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    schedule.view()
    output, _ = capsys.readouterr()
    assert "[ACC DATA]" in output
    assert schedule.children[0].dag_name == "ACC_data_1"


def test_explicit_directive():
    '''Check code generation for a single explicit loop containing a
    kernel with a pre-existing (openacc kernels) directive.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "explicit_do.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('explicit_do').schedule
    acc_trans = TransInfo().get_trans_name('ACCKernelsTrans')
    schedule, _ = acc_trans.apply(schedule.children, default_present=True)
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("  REAL, DIMENSION(jpi, jpj, jpk) :: umask\n"
            "  !$ACC DATA COPYOUT(umask)\n"
            "  !$ACC KERNELS DEFAULT(PRESENT)\n"
            "  DO jk = 1, jpk") in gen_code

    assert ("  END DO\n"
            "  !$ACC END KERNELS\n"
            "  !$ACC END DATA\n"
            "END PROGRAM explicit_do") in gen_code


def test_code_block():
    '''Check code generation for a mixture of loops and code blocks.'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "code_block.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('code_block').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("  REAL, ALLOCATABLE, DIMENSION(:, :, :) :: umask\n"
            "  !$ACC DATA COPYOUT(umask)\n"
            "  WRITE(*, FMT = *) \"Hello world\"") in gen_code

    assert ("  DEALLOCATE(umask)\n"
            "  !$ACC END DATA\n"
            "END PROGRAM code_block") in gen_code


def test_code_block_noalloc():
    '''Check code generation for a mixture of loops and code blocks,
    skipping allocate and deallocate statements.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "code_block.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('code_block').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children[1:5])
    gen_code = str(psy.gen)

    assert ("  ALLOCATE(umask(jpi, jpj, jpk))\n"
            "  !$ACC DATA COPYOUT(umask)\n"
            "  umask(1, 1, :) = 0.0D0\n") in gen_code

    assert ("  END DO\n"
            "  !$ACC END DATA\n"
            "  WRITE(*, FMT = *) \"Goodbye world\"") in gen_code


def test_code_block_noalloc_kernels():
    '''Check code generation for a mixture of loops and code blocks,
    skipping allocate and deallocate statements and with a kernels
    directive. Apply kernels transformations second in this example.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "code_block.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('code_block').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children[1:4])
    acc_trans = TransInfo().get_trans_name('ACCKernelsTrans')
    schedule, _ = acc_trans.apply(schedule.children[1].children[0:3],
                                  default_present=True)
    gen_code = str(psy.gen)

    assert ("  ALLOCATE(umask(jpi, jpj, jpk))\n"
            "  !$ACC DATA COPYOUT(umask)\n"
            "  !$ACC KERNELS DEFAULT(PRESENT)\n"
            "  umask(1, 1, :) = 0.0D0\n") in gen_code

    assert ("  END DO\n"
            "  !$ACC END KERNELS\n"
            "  !$ACC END DATA\n"
            "  DO iloop = 1, jpi") in gen_code


def test_single_code_block():
    '''Check code generation for a mixture of loops and code blocks.'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "afunction.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('afunction').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("  INTEGER :: num\n"
            "  !$ACC DATA\n"
            "  IF (iarg > 0) THEN") in gen_code

    assert ("  END IF\n"
            "  !$ACC END DATA\n"
            "END FUNCTION afunction") in gen_code


def test_array_syntax():
    '''Check code generation for a mixture of loops and code blocks.'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "array_syntax.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('tra_ldf_iso').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("  REAL(KIND = wp), DIMENSION(jpi, jpj, jpk) :: zdit, zdjt, "
            "zftu, zftv, ztfw\n"
            "  !$ACC DATA COPYOUT(zftv,zftu)\n"
            "  zftv(:, :, :) = 0.0D0" in gen_code)

    assert ("  zftu(:, :, 1) = 1.0D0\n"
            "  !$ACC END DATA\n"
            "END SUBROUTINE tra_ldf_iso" in gen_code)


def test_multi_data():
    '''Check code generation with multiple data directives.'''
    _, invoke_info = parse(os.path.join(BASE_PATH, "imperfect_nest.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('imperfect_nest').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children[0].children[0:2])
    schedule, _ = acc_trans.apply(schedule.children[0].children[1:3])
    gen_code = str(psy.gen)

    assert ("  DO jk = 1, jpkm1\n"
            "    !$ACC DATA COPYIN(ptb,wmask) "
            "COPYOUT(zdk1t,zdkt)\n"
            "    DO jj = 1, jpj, 1") in gen_code

    assert ("    END IF\n"
            "    !$ACC END DATA\n"
            "    !$ACC DATA COPYIN(pahu,e2_e1u,e3u_n,wmask,e2u,uslp,zdit,"
            "zdkt,zdk1t,umask,pta,zftv,r1_e1e2t,e3t_n) "
            "COPYOUT(zftu,pta)\n"
            "    DO jj = 1, jpjm1") in gen_code

    assert ("    END DO\n"
            "    !$ACC END DATA\n"
            "  END DO") in gen_code


def test_replicated_loop():
    '''Check code generation with two loops that have the same
    structure.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "replicated.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('replicate').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children[0:1])
    schedule, _ = acc_trans.apply(schedule.children[1:2])
    gen_code = str(psy.gen)

    assert ("  !$ACC DATA COPYOUT(zwx)\n"
            "  zwx(:, :) = 0.E0\n"
            "  !$ACC END DATA\n"
            "  !$ACC DATA COPYOUT(zwx)\n"
            "  zwx(:, :) = 0.E0\n"
            "  !$ACC END DATA" in gen_code)


def test_data_ref():
    '''Check code generation with an array accessed via a derived type.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "data_ref.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('data_ref').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("!$ACC DATA COPYIN(a) COPYOUT(prof,prof%npind)") in gen_code


def test_array_section():
    '''Check code generation with a arrays accessed via an array section.

    '''
    _, invoke_info = parse(os.path.join(BASE_PATH, "array_section.f90"),
                           api=API, line_length=False)
    psy = PSyFactory(API, distributed_memory=False).create(invoke_info)
    schedule = psy.invokes.get('array_section').schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children)
    gen_code = str(psy.gen)

    assert ("!$ACC DATA COPYIN(b,c) COPYOUT(a)") in gen_code


def test_kind_parameter(parser):
    ''' Check that we don't attempt to put kind parameters into the list
    of variables to copyin/out. '''
    reader = FortranStringReader("program kind_param\n"
                                 "real(kind=wp) :: sto_tmp(5)\n"
                                 "do ji = 1,jpj\n"
                                 "sto_tmp(ji) = 0._wp\n"
                                 "end do\n"
                                 "end program kind_param\n")
    code = parser(reader)
    psy = PSyFactory(API, distributed_memory=False).create(code)
    schedule = psy.invokes.invoke_list[0].schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children[0:1])
    gen_code = str(psy.gen)

    assert "copyin(wp)" not in gen_code.lower()


def test_fn_call(parser):
    ''' Check that we don't attempt to put function names into the list
    of variables we copyin/out. '''
    reader = FortranStringReader("program fn_call\n"
                                 "real(kind=wp) :: sto_tmp(5)\n"
                                 "do ji = 1,jpj\n"
                                 "sto_tmp(ji) = my_func()\n"
                                 "end do\n"
                                 "end program fn_call\n")
    code = parser(reader)
    psy = PSyFactory(API, distributed_memory=False).create(code)
    schedule = psy.invokes.invoke_list[0].schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    schedule, _ = acc_trans.apply(schedule.children[0:1])
    gen_code = str(psy.gen)
    assert "copyin(my_func)" not in gen_code.lower()


def test_no_copyin_intrinsics(parser):
    ''' Check that we don't generate a copyin/out for Fortran instrinsic
    functions (i.e. we don't mistake them for array accesses). '''
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    for intrinsic in ["cos(ji)", "sin(ji)", "tan(ji)", "atan(ji)",
                      "mod(ji, 5)"]:
        reader = FortranStringReader(
            "program call_intrinsic\n"
            "real(kind=wp) :: sto_tmp(5)\n"
            "do ji = 1,jpj\n"
            "sto_tmp(ji) = {0}\n"
            "end do\n"
            "end program call_intrinsic\n".format(intrinsic))
        code = parser(reader)
        psy = PSyFactory(API, distributed_memory=False).create(code)
        schedule = psy.invokes.invoke_list[0].schedule
        schedule, _ = acc_trans.apply(schedule.children[0:1])
        gen_code = str(psy.gen)
        idx = intrinsic.index("(")
        assert "copyin({0})".format(intrinsic[0:idx]) not in gen_code.lower()


@pytest.mark.xfail(reason="Needs updated RegionTrans.validate method, #292")
def test_no_code_blocks(parser):
    ''' Check that we refuse to include CodeBlocks (i.e. code that we
    don't recognise) within a data region. '''
    reader = FortranStringReader("program write_out\n"
                                 "real(kind=wp) :: sto_tmp(5)\n"
                                 "do ji = 1,jpj\n"
                                 "read(*,*) sto_tmp(ji)\n"
                                 "end do\n"
                                 "do ji = 1,jpj\n"
                                 "write(*,*) sto_tmp(ji)\n"
                                 "end do\n"
                                 "end program write_out\n")
    code = parser(reader)
    psy = PSyFactory(API, distributed_memory=False).create(code)
    schedule = psy.invokes.invoke_list[0].schedule
    acc_trans = TransInfo().get_trans_name('ACCDataTrans')
    with pytest.raises(TransformationError) as err:
        _, _ = acc_trans.apply(schedule.children[0:1])
    assert "cannot enclose CodeBlock'>' in ACCDataTrans" in str(err)
    with pytest.raises(TransformationError) as err:
        _, _ = acc_trans.apply(schedule.children[1:2])
    assert "cannot enclose CodeBlock'>' in ACCDataTrans" in str(err)