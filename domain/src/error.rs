#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DomainError {
    EmptyName,
    EmptyDimensionName,
    NonPositiveMeasure,
    DuplicateDimensionName,
    MissingDimension,
    UnexpectedDimension,
    UnknownUnit,
    UnknownDiameter,
}
