!-------------------------------------------------------------------------------
! (c) The copyright relating to this work is owned jointly by the Crown,
! Met Office and NERC 2015.
! However, it has been created with the help of the GungHo Consortium,
! whose members are identified at https://puma.nerc.ac.uk/trac/GungHo/wiki
!-------------------------------------------------------------------------------
! Author A. Porter STFC Daresbury Lab
! Funded by the GOcean project

PROGRAM single_invoke_test

  ! Fake Fortran program for testing aspects of
  ! the PSyclone code generation system.

  use kind_params_mod
  use grid_mod
  use field_mod
  use kernel_unsupported_offset_mod, only: compute_z
  implicit none

  type(grid_type), target :: model_grid
  type(r2d_field) :: ufld, vfld, hfld, zfld

  !> Loop counter for time-stepping loop
  INTEGER :: ncycle

  ! Create the model grid
  model_grid = grid_type(GO_ARAKAWA_C,                        &
                         (/GO_BC_PERIODIC,GO_BC_PERIODIC,GO_BC_NONE/) )

  ! Create fields on this grid
  ufld = r2d_field(model_grid, GO_U_POINTS)
  vfld = r2d_field(model_grid, GO_V_POINTS)
  hfld = r2d_field(model_grid, GO_T_POINTS)
  zfld = r2d_field(model_grid, GO_F_POINTS)

  !  ** Start of time loop ** 
  DO ncycle=1,100
    
    call invoke( compute_z(zfld, hfld, ufld, vfld) )

  END DO

  !===================================================

END PROGRAM single_invoke_test
