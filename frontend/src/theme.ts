import { extendTheme, type ThemeConfig } from '@chakra-ui/react';
import { mode, type StyleFunctionProps } from '@chakra-ui/theme-tools';

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  colors: {
    brand: {
      50: '#f4fce3',
      100: '#e4f7c3',
      200: '#ccef86',
      300: '#b5e54e',
      400: '#a3c940',
      500: '#8ab534',
      600: '#6f9a28',
      700: '#557a1e',
      800: '#3d5c15',
      900: '#263d0d',
    },
    orange: {
      50: '#fef7f0',
      100: '#fde8d5',
      200: '#fad0ab',
      300: '#f5b07a',
      400: '#e8854a',
      500: '#d4702f',
      600: '#b85a21',
      700: '#954518',
      800: '#733412',
      900: '#5c280e',
    },
    surface: {
      50: '#f7f8fa',
      100: '#ebedf0',
      200: '#d1d5db',
      300: '#9ca3af',
      400: '#6b7280',
      500: '#4b5563',
      600: '#374151',
      700: '#2a2f38',
      800: '#1e222a',
      900: '#161a21',
      950: '#0f1117',
    },
    accent: {
      green: '#a3c940',
      orange: '#e8854a',
      blue: '#4a9eff',
      red: '#ef4444',
    },
  },
  fonts: {
    heading: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  styles: {
    global: (props: StyleFunctionProps) => ({
      body: {
        bg: mode('gray.50', 'surface.950')(props),
        color: mode('gray.800', 'gray.100')(props),
      },
      '*::placeholder': {
        color: mode('gray.400', 'gray.500')(props),
      },
    }),
  },
  borders: {
    subtle: '1px solid rgba(255, 255, 255, 0.06)',
  },
  radii: {
    sm: '6px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    '2xl': '20px',
  },
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'brand',
      },
      baseStyle: {
        borderRadius: 'lg',
        fontWeight: '500',
        transition: 'all 0.2s',
      },
      variants: {
        solid: (_props: StyleFunctionProps) => ({
          bg: 'brand.500',
          color: 'white',
          _hover: {
            bg: 'brand.400',
            transform: 'translateY(-1px)',
            boxShadow: '0 4px 12px rgba(163, 201, 64, 0.3)',
          },
          _active: {
            bg: 'brand.600',
            transform: 'translateY(0)',
          },
        }),
        ghost: (props: StyleFunctionProps) => ({
          color: mode('gray.600', 'gray.300')(props),
          _hover: {
            bg: mode('gray.100', 'whiteAlpha.100')(props),
            color: mode('gray.800', 'gray.100')(props),
          },
        }),
        outline: (props: StyleFunctionProps) => ({
          borderColor: mode('gray.200', 'whiteAlpha.200')(props),
          color: mode('gray.600', 'gray.300')(props),
          _hover: {
            bg: mode('gray.50', 'whiteAlpha.50')(props),
            borderColor: mode('gray.300', 'whiteAlpha.300')(props),
          },
        }),
      },
    },
    Card: {
      baseStyle: (props: StyleFunctionProps) => ({
        container: {
          bg: mode('white', 'surface.800')(props),
          borderRadius: 'xl',
          borderWidth: '1px',
          borderColor: mode('gray.200', 'whiteAlpha.100')(props),
          boxShadow: mode('0 4px 24px rgba(0, 0, 0, 0.08)', '0 4px 24px rgba(0, 0, 0, 0.2)')(props),
        },
      }),
    },
    Input: {
      variants: {
        outline: (props: StyleFunctionProps) => ({
          field: {
            bg: mode('white', 'surface.900')(props),
            borderColor: mode('gray.200', 'whiteAlpha.100')(props),
            borderRadius: 'lg',
            _hover: {
              borderColor: mode('gray.300', 'whiteAlpha.200')(props),
            },
            _focus: {
              borderColor: 'brand.400',
              boxShadow: '0 0 0 1px var(--chakra-colors-brand-400)',
            },
            _placeholder: {
              color: mode('gray.400', 'gray.500')(props),
            },
          },
        }),
      },
      defaultProps: {
        variant: 'outline',
      },
    },
    Select: {
      variants: {
        outline: (props: StyleFunctionProps) => ({
          field: {
            bg: mode('white', 'surface.900')(props),
            borderColor: mode('gray.200', 'whiteAlpha.100')(props),
            borderRadius: 'lg',
            _hover: {
              borderColor: mode('gray.300', 'whiteAlpha.200')(props),
            },
            _focus: {
              borderColor: 'brand.400',
              boxShadow: '0 0 0 1px var(--chakra-colors-brand-400)',
            },
          },
        }),
      },
    },
    Textarea: {
      variants: {
        outline: (props: StyleFunctionProps) => ({
          bg: mode('white', 'surface.900')(props),
          borderColor: mode('gray.200', 'whiteAlpha.100')(props),
          borderRadius: 'lg',
          _hover: {
            borderColor: mode('gray.300', 'whiteAlpha.200')(props),
          },
          _focus: {
            borderColor: 'brand.400',
            boxShadow: '0 0 0 1px var(--chakra-colors-brand-400)',
          },
        }),
      },
    },
    Modal: {
      baseStyle: (props: StyleFunctionProps) => ({
        dialog: {
          bg: mode('white', 'surface.800')(props),
          borderRadius: 'xl',
          borderWidth: '1px',
          borderColor: mode('gray.200', 'whiteAlpha.100')(props),
        },
      }),
    },
    Menu: {
      baseStyle: (props: StyleFunctionProps) => ({
        list: {
          bg: mode('white', 'surface.800')(props),
          borderColor: mode('gray.200', 'whiteAlpha.100')(props),
          borderRadius: 'lg',
          boxShadow: mode('0 8px 32px rgba(0, 0, 0, 0.12)', '0 8px 32px rgba(0, 0, 0, 0.4)')(props),
        },
        item: {
          bg: 'transparent',
          _hover: {
            bg: mode('gray.100', 'whiteAlpha.100')(props),
          },
          _focus: {
            bg: mode('gray.100', 'whiteAlpha.100')(props),
          },
        },
      }),
    },
    Tooltip: {
      baseStyle: (props: StyleFunctionProps) => ({
        bg: mode('gray.700', 'surface.700')(props),
        color: 'gray.100',
        borderRadius: 'md',
        px: 3,
        py: 2,
        fontSize: 'xs',
      }),
    },
    Badge: {
      baseStyle: {
        borderRadius: 'md',
        textTransform: 'uppercase',
        fontSize: '2xs',
        fontWeight: '600',
        letterSpacing: '0.05em',
      },
    },
    Tabs: {
      variants: {
        line: (props: StyleFunctionProps) => ({
          tab: {
            color: mode('gray.500', 'gray.400')(props),
            _selected: {
              color: 'brand.400',
              borderColor: 'brand.400',
            },
            _hover: {
              color: mode('gray.700', 'gray.200')(props),
            },
          },
        }),
      },
    },
    Accordion: {
      baseStyle: (props: StyleFunctionProps) => ({
        container: {
          borderColor: mode('gray.200', 'whiteAlpha.100')(props),
        },
        button: {
          _hover: {
            bg: mode('gray.50', 'whiteAlpha.50')(props),
          },
        },
      }),
    },
  },
  shadows: {
    'dark-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2)',
    'glow-brand': '0 0 20px rgba(163, 201, 64, 0.15)',
    'card': '0 4px 24px rgba(0, 0, 0, 0.2)',
  },
});

export default theme;
