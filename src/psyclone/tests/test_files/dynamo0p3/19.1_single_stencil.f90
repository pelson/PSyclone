! Author R. Ford STFC Daresbury Lab
program single_stencil
  ! Description: single stencil specified in an invoke call
  use testkern_stencil_mod, only: testkern_stencil_type
  use inf,      only: field_type
  implicit none
  type(field_type) :: f1,f2,f3,f4
  integer :: f2_extent=1

  call invoke(                                      &
       testkern_stencil_type(f1,f2,f2_extent,f3,f4) &
       )

end program single_stencil
