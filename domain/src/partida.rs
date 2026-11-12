use crate::dimension::Dimension;
use crate::error::DomainError;
use crate::quantity::Quantity;
use crate::unit::Unit;

#[derive(Debug, Clone, PartialEq)]
pub struct Partida {
    name: String,
    unit: Unit,
    dimensions: Vec<Dimension>,
    quantity: Quantity,
}

impl Partida {
    pub fn try_new(
        name: &str,
        unit: Unit,
        dimensions: Vec<Dimension>,
    ) -> Result<Self, DomainError> {
        let name = name.trim();
        if name.is_empty() {
            return Err(DomainError::EmptyName);
        }
        let product = quantity_for(unit, &dimensions)?;
        Ok(Self {
            name: name.to_string(),
            unit,
            dimensions,
            quantity: Quantity::new(product),
        })
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn unit(&self) -> Unit {
        self.unit
    }

    pub fn dimensions(&self) -> &[Dimension] {
        &self.dimensions
    }

    pub fn quantity(&self) -> Quantity {
        self.quantity
    }
}

fn quantity_for(unit: Unit, dimensions: &[Dimension]) -> Result<f64, DomainError> {
    if has_duplicate_name(dimensions) {
        return Err(DomainError::DuplicateDimensionName);
    }
    let required = unit.required_names();
    for dimension in dimensions {
        if !required.contains(&dimension.name()) {
            return Err(DomainError::UnexpectedDimension);
        }
    }
    let mut measures = Vec::new();
    for name in required {
        let Some(dimension) = dimensions.iter().find(|item| item.name() == *name) else {
            return Err(DomainError::MissingDimension);
        };
        measures.push(dimension.measure());
    }
    crate::decimal::product(&measures)
}

fn has_duplicate_name(dimensions: &[Dimension]) -> bool {
    for (index, dimension) in dimensions.iter().enumerate() {
        if dimensions[..index]
            .iter()
            .any(|earlier| earlier.name() == dimension.name())
        {
            return true;
        }
    }
    false
}
