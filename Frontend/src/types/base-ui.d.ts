declare module '@base-ui/react/button' {
  import type * as React from 'react'

  export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    focusableWhenDisabled?: boolean
    nativeButton?: boolean
    render?: React.ReactElement | ((props: unknown) => React.ReactElement)
  }

  export const Button: React.ForwardRefExoticComponent<
    ButtonProps & React.RefAttributes<HTMLButtonElement>
  >

  export const ButtonDataAttributes: Record<string, string>
}
