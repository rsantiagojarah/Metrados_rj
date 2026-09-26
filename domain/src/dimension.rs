use crate::error::DomainError;

#[derive(Debug, Clone, PartialEq)]
pub struct Dimension {
    name: String,
    measure: f64,
}

impl Dimension {
    pub fn try_new(name: &str, measure: f64) -> Result<Self, DomainError> {
        let name = name.trim();
        if name.is_empty() {
            return Err(DomainError::EmptyDimensionName);
        }
        if !measure.is_finite() || measure <= 0.0 {
            return Err(DomainError::NonPositiveMeasure);
        }
        Ok(Self {
            name: name.to_string(),
            measure,
        })
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn measure(&self) -> f64 {
        self.measure
    }
}
