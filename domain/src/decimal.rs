//! Decimal arithmetic at the calculation boundary; presentation never owns totals.
use crate::DomainError;
use bigdecimal::{BigDecimal, RoundingMode, ToPrimitive, Zero};

fn decimal(value: f64) -> Result<BigDecimal, DomainError> {
    if !value.is_finite() {
        return Err(DomainError::NonPositiveMeasure);
    }
    value
        .to_string()
        .parse()
        .map_err(|_| DomainError::NonPositiveMeasure)
}

fn number(value: &BigDecimal) -> Result<f64, DomainError> {
    let result = value.to_f64().ok_or(DomainError::NonPositiveMeasure)?;
    if !result.is_finite() || (result == 0.0 && !value.is_zero()) {
        return Err(DomainError::NonPositiveMeasure);
    }
    Ok(result)
}

pub fn product(values: &[f64]) -> Result<f64, DomainError> {
    let mut result = BigDecimal::from(1);
    for value in values {
        result *= decimal(*value)?;
    }
    number(&result)
}

pub(crate) fn sum(values: &[f64]) -> Result<f64, DomainError> {
    let mut result = BigDecimal::zero();
    for value in values {
        result += decimal(*value)?;
        number(&result)?;
    }
    number(&result)
}

pub fn round_quantity(value: f64) -> Result<f64, DomainError> {
    number(&decimal(value)?.with_scale_round(2, RoundingMode::HalfUp))
}

pub(crate) fn rounded_total(values: &[f64]) -> Result<f64, DomainError> {
    let mut result = BigDecimal::zero();
    for value in values {
        result += decimal(*value)?.with_scale_round(2, RoundingMode::HalfUp);
        number(&result)?;
    }
    number(&result)
}
