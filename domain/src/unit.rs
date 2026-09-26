use crate::error::DomainError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Unit {
    LinearMeter,
    SquareMeter,
    CubicMeter,
    Each,
}

impl Unit {
    pub fn parse(value: &str) -> Result<Self, DomainError> {
        match value.trim() {
            "m" => Ok(Self::LinearMeter),
            "m2" => Ok(Self::SquareMeter),
            "m3" => Ok(Self::CubicMeter),
            "und" => Ok(Self::Each),
            _ => Err(DomainError::UnknownUnit),
        }
    }

    pub fn required_names(self) -> &'static [&'static str] {
        match self {
            Self::LinearMeter => &["longitud"],
            Self::SquareMeter => &["largo", "ancho"],
            Self::CubicMeter => &["largo", "ancho", "alto"],
            Self::Each => &["veces"],
        }
    }
}
