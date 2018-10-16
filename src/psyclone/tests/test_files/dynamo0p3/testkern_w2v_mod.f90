! -----------------------------------------------------------------------------
! BSD 3-Clause License
!
! Copyright (c) 2018, Science and Technology Facilities Council
! All rights reserved.
!
! Redistribution and use in source and binary forms, with or without
! modification, are permitted provided that the following conditions are met:
!
! * Redistributions of source code must retain the above copyright notice, this
!   list of conditions and the following disclaimer.
!
! * Redistributions in binary form must reproduce the above copyright notice,
!   this list of conditions and the following disclaimer in the documentation
!   and/or other materials provided with the distribution.
!
! * Neither the name of the copyright holder nor the names of its
!   contributors may be used to endorse or promote products derived from
!   this software without specific prior written permission.
!
! THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
! "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
! LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
! FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
! COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
! INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
! BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
! LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
! CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
! LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
! ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
! POSSIBILITY OF SUCH DAMAGE.
! -----------------------------------------------------------------------------
! Author I. Kavcic Met Office

module testkern_w2v_mod

  use argument_mod
  use kernel_mod
  use constants_mod

  implicit none

  ! Description: discontinuous field readwriter (w2v) and two readers
  ! (wtheta and w2broken)
  type, extends(kernel_type) :: testkern_w2v_type
     type(arg_type), dimension(3) :: meta_args =        &
          (/ arg_type(gh_field, gh_readwrite, w2v),     &
             arg_type(gh_field, gh_read,      wtheta),  &
             arg_type(gh_field, gh_read,      w2broken) &
           /)
     integer :: iterates_over = cells
   contains
     procedure, nopass :: code => testkern_w2v_code
  end type testkern_w2v_type

contains

  subroutine testkern_w2v_code(nlayers,                             &
                               field1_w2v,                          &
                               field2_wtheta,                       &
                               field3_w2broken,                     &
                               ndf_w2v, undf_w2v, map_w2v,          &
                               ndf_wtheta, undf_wtheta, map_wtheta, &
                               ndf_w2broken, undf_w2broken, map_w2broken)

    implicit none

    integer, intent(in) :: nlayers
    integer, intent(in) :: ndf_w2v
    integer, intent(in) :: undf_w2v
    integer, intent(in) :: ndf_wtheta
    integer, intent(in) :: undf_wtheta
    integer, intent(in) :: ndf_w2broken
    integer, intent(in) :: undf_w2broken
    real(kind=r_def), intent(inout), dimension(undf_w2v)   :: field1_w2v
    real(kind=r_def), intent(in), dimension(undf_wtheta)   :: field2_wtheta
    real(kind=r_def), intent(in), dimension(undf_w2broken) :: field3_w2broken
    integer, intent(in), dimension(ndf_w2v)      :: map_w2v
    integer, intent(in), dimension(ndf_wtheta)   :: map_wtheta
    integer, intent(in), dimension(ndf_w2broken) :: map_w2broken


  end subroutine testkern_w2v_code

end module testkern_w2v_mod
