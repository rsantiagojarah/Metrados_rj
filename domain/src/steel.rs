use crate::error::DomainError;

const STEEL_DENSITY: f64 = 7850.0;

#[derive(Debug, Clone, PartialEq)]
pub struct SteelQuantity {
    pub length: f64,
    pub kg_per_m: f64,
    pub weight: f64,
}

/// Long = largo + gancho + empalme; Kg = elem × Long × n° × kg/m(Ø) × veces.
pub fn sheet_steel(
    largo: f64,
    gancho: f64,
    empalme: f64,
    diameter: &str,
    bars: f64,
    elements: f64,
    veces: f64,
) -> Result<SteelQuantity, DomainError> {
    require_positive(largo)?;
    require_non_negative(gancho)?;
    require_non_negative(empalme)?;
    require_positive(bars)?;
    require_positive(elements)?;
    require_positive(veces)?;
    let diameter_m = parse_diameter_meters(diameter)?;
    let length = largo + gancho + empalme;
    let kg_per_m = std::f64::consts::PI / 4.0 * diameter_m * diameter_m * STEEL_DENSITY;
    let weight = elements * length * bars * kg_per_m * veces;
    if !length.is_finite() || !kg_per_m.is_finite() || !weight.is_finite() || weight <= 0.0 {
        return Err(DomainError::NonPositiveMeasure);
    }
    Ok(SteelQuantity {
        length,
        kg_per_m,
        weight,
    })
}

fn require_positive(value: f64) -> Result<(), DomainError> {
    if !value.is_finite() || value <= 0.0 {
        return Err(DomainError::NonPositiveMeasure);
    }
    Ok(())
}

fn require_non_negative(value: f64) -> Result<(), DomainError> {
    if !value.is_finite() || value < 0.0 {
        return Err(DomainError::NonPositiveMeasure);
    }
    Ok(())
}

fn parse_diameter_meters(text: &str) -> Result<f64, DomainError> {
    let trimmed = text.trim().trim_start_matches(['Ø', 'ø', '∅', 'Φ', 'φ']);
    let normalized = trimmed
        .to_lowercase()
        .replace("''", "\"")
        .replace('″', "\"")
        .replace('-', " ");
    let compact: String = normalized.chars().filter(|c| !c.is_whitespace()).collect();
    if let Some(mm) = compact.strip_suffix("mm") {
        return meters_from_mm(parse_simple(mm)?);
    }
    if compact.ends_with('"') || compact.ends_with("pulg") {
        let inches = normalized.replace('"', "").replace("pulg", "");
        return inches_to_meters(parse_mixed(&inches)?);
    }
    if compact.contains('/') {
        return inches_to_meters(parse_mixed(&normalized)?);
    }
    let value = parse_simple(&compact)?;
    if value >= 1.0 {
        return meters_from_mm(value);
    }
    require_positive(value)?;
    Ok(value)
}

fn parse_mixed(text: &str) -> Result<f64, DomainError> {
    let mut total = 0.0;
    let mut seen = false;
    for part in text.split_whitespace() {
        let cleaned: String = part.chars().filter(|c| *c != '"').collect();
        if cleaned.is_empty() || cleaned == "pulg" {
            continue;
        }
        total += parse_simple(&cleaned)?;
        seen = true;
    }
    if !seen {
        return Err(DomainError::UnknownDiameter);
    }
    Ok(total)
}

fn parse_simple(part: &str) -> Result<f64, DomainError> {
    if let Some((num, den)) = part.split_once('/') {
        let num: f64 = num.parse().map_err(|_| DomainError::UnknownDiameter)?;
        let den: f64 = den.parse().map_err(|_| DomainError::UnknownDiameter)?;
        if den == 0.0 || !num.is_finite() || !den.is_finite() {
            return Err(DomainError::UnknownDiameter);
        }
        return Ok(num / den);
    }
    part.parse().map_err(|_| DomainError::UnknownDiameter)
}

fn meters_from_mm(mm: f64) -> Result<f64, DomainError> {
    require_positive(mm)?;
    Ok(mm / 1000.0)
}

fn inches_to_meters(inches: f64) -> Result<f64, DomainError> {
    require_positive(inches)?;
    Ok(inches * 0.0254)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stirrup_row_matches_developed_length_and_weight() {
        let quantity = sheet_steel(10.85, 0.61, 1.15, r#"1""#, 53.0, 2.0, 1.0).unwrap();
        assert!((quantity.length - 12.61).abs() < 1e-9);
        assert!((quantity.kg_per_m - 3.978).abs() < 0.002);
        let expected = 2.0 * 12.61 * 53.0 * quantity.kg_per_m;
        assert!((quantity.weight - expected).abs() < 1e-9);
        let twice = sheet_steel(10.85, 0.61, 1.15, r#"1""#, 53.0, 2.0, 2.0).unwrap();
        assert!((twice.weight - expected * 2.0).abs() < 1e-9);
    }

    #[test]
    fn zero_hooks_and_splices_keep_length_equal_to_largo() {
        let quantity = sheet_steel(2.15, 0.0, 0.0, r#"3/4""#, 6.0, 2.0, 1.0).unwrap();
        assert!((quantity.length - 2.15).abs() < 1e-9);
        assert!((quantity.kg_per_m - 2.237).abs() < 0.002);
    }

    #[test]
    fn metric_and_mixed_diameters() {
        let eight = sheet_steel(1.0, 0.0, 0.0, "8mm", 1.0, 1.0, 1.0).unwrap();
        assert!((eight.kg_per_m - 0.395).abs() < 0.002);
        let mixed = sheet_steel(1.0, 0.0, 0.0, r#"1 3/8""#, 1.0, 1.0, 1.0).unwrap();
        assert!((mixed.kg_per_m - 7.517).abs() < 0.01);
    }

    #[test]
    fn invalid_steel_inputs_are_rejected() {
        assert!(sheet_steel(0.0, 0.0, 0.0, r#"1""#, 1.0, 1.0, 1.0).is_err());
        assert!(sheet_steel(1.0, -0.1, 0.0, r#"1""#, 1.0, 1.0, 1.0).is_err());
        assert!(sheet_steel(1.0, 0.0, 0.0, "", 1.0, 1.0, 1.0).is_err());
        assert!(sheet_steel(1.0, 0.0, 0.0, "xyz", 1.0, 1.0, 1.0).is_err());
        assert!(sheet_steel(1.0, 0.0, 0.0, r#"1""#, 0.0, 1.0, 1.0).is_err());
        assert!(sheet_steel(1.0, 0.0, 0.0, r#"1""#, 1.0, 1.0, 0.0).is_err());
        assert_eq!(
            sheet_steel(1.0, 0.0, 0.0, "abc", 1.0, 1.0, 1.0),
            Err(DomainError::UnknownDiameter)
        );
    }
}
